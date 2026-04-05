import asyncio
from datetime import timedelta, datetime
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.models import Order, OrderStatus, User, WorkSlot
from database.requests import get_employee_daily_hours, get_user_by_telegram_id, create_work_slot
from services.google_sheets import google_sheets
from keyboards.staff_kb import accept_order_kb
import config


class OrderDispatcher:
    def __init__(self, bot: Bot, session):
        self.bot = bot
        self.session = session

    async def get_weekly_order_count(self, employee_id: int, date: datetime):
        start_of_week = (date - timedelta(days=date.weekday())).replace(hour=0, minute=0)
        stmt = select(func.count(Order.id)).where(
            Order.employee_id == employee_id,
            Order.order_date >= start_of_week,
            Order.status != OrderStatus.CANCELLED
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def find_available_employees(self, order: Order):
        schedule = await asyncio.to_thread(google_sheets.get_schedule)
        order_date_str = order.order_date.strftime('%d.%m.%Y')
        candidates = []

        duration = order.service.duration_minutes if order.service else 120
        needed_hours = (duration + 60) / 60

        for record in schedule:
            if str(record.get('Дата')) != order_date_str:
                continue

            tg_id = record.get('ID сотрудника')
            if not tg_id: continue

            user = await get_user_by_telegram_id(self.session, int(tg_id))
            if not user or user.is_blocked: continue

            daily = await get_employee_daily_hours(self.session, user.id, order.order_date)

            if daily + needed_hours > 10:
                continue

            weekly_hours_stmt = select(
                func.sum(func.julianday(WorkSlot.end_time) - func.julianday(WorkSlot.start_time)) * 24).where(
                WorkSlot.employee_id == user.id)

            weekly_count = await self.get_weekly_order_count(user.id, order.order_date)

            candidates.append({
                'user': user,
                'daily_load': daily,
                'weekly_count': weekly_count,
                'name': user.full_name
            })
        return candidates

    async def send_offers_to_staff(self, order_id: int):
        result = await self.session.execute(
            select(Order).options(selectinload(Order.service)).where(Order.id == order_id)
        )
        order = result.scalars().first()
        if not order: return

        candidates = await self.find_available_employees(order)

        if not candidates:
            await self.notify_admin_no_staff(order)
            return

        text = (f" *Новое предложение заказа #{order.id}*\n\n"
                f" Детали: {order.custom_details or (order.service.name if order.service else 'Уборка')}\n"
                f" Дата: {order.order_date.strftime('%d.%m.%Y %H:%M')}\n"
                f" Адрес: {order.address}\n"
                f" Выплата: {order.total_price} BYN\n\n"
                f"У вас есть 1 час, чтобы забрать этот заказ.")

        for c in candidates:
            try:
                await self.bot.send_message(c['user'].telegram_id, text, parse_mode="Markdown",
                                            reply_markup=accept_order_kb(order.id))
            except TelegramAPIError:
                pass

    async def auto_assign_logic(self, order_id: int):
        result = await self.session.execute(
            select(Order).options(selectinload(Order.service)).where(Order.id == order_id)
        )
        order = result.scalars().first()

        if not order or order.status != OrderStatus.AWAITING:
            return

        candidates = await self.find_available_employees(order)
        if not candidates:
            await self.notify_admin_no_staff(order)
            return

        candidates.sort(key=lambda x: (x['daily_load'], x['weekly_count']))

        best = candidates[0]['user']

        order.status = OrderStatus.ASSIGNED
        order.employee_id = best.id

        duration = order.service.duration_minutes if order.service else 120
        await create_work_slot(self.session, best.id, order.id, 'travel_to',
                               order.order_date - timedelta(minutes=30), order.order_date)
        await create_work_slot(self.session, best.id, order.id, 'cleaning',
                               order.order_date, order.order_date + timedelta(minutes=duration))
        await create_work_slot(self.session, best.id, order.id, 'travel_from',
                               order.order_date + timedelta(minutes=duration),
                               order.order_date + timedelta(minutes=duration + 30))

        await self.session.commit()

        try:
            await self.bot.send_message(
                best.telegram_id,
                f" *Заказ #{order.id} назначен вам автоматически*\n\n"
                f"Так как заказ не был принят вовремя, система выбрала вас на основе наименьшей загрузки.\n"
                f"Пожалуйста, ознакомьтесь с деталями в меню 'Мой график'.",
                parse_mode="Markdown"
            )
        except:
            pass

    async def notify_admin_no_staff(self, order):
        for admin_id in config.ADMIN_IDS:
            try:
                await self.bot.send_message(
                    admin_id,
                    f" *ВНИМАНИЕ: Заказ без исполнителя*\n\n"
                    f"Система не смогла найти свободного сотрудника для заказа #{order.id}.\n"
                    f"Причина: Превышение лимитов времени или отсутствие в графике.\n"
                    f"Требуется ручное назначение!",
                    parse_mode="Markdown"
                )
            except:
                pass
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from sqlalchemy import select

from database.engine import AsyncSessionLocal
from database.models import Order, OrderStatus, User
from services.google_sheets import google_sheets
import config

logger = logging.getLogger(__name__)


async def sync_schedule_task():
    logger.info("Обновление графиков из таблиц...")
    await asyncio.to_thread(google_sheets.get_schedule)


async def check_inventory_task(bot):
    logger.info("Проверка складских запасов...")
    low_stock_items = await asyncio.to_thread(google_sheets.get_low_stock_items)

    if low_stock_items:
        msg = " *ВНИМАНИЕ! Низкий остаток на складе:*\n\n"
        for item in low_stock_items:
            msg += f"• {item.get('Название')}: {item.get('Остаток')} {item.get('Ед. изм.')}\n"

        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(admin_id, msg, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Ошибка уведомления админа {admin_id}: {e}")


async def daily_equipment_task(bot):
    logger.info("Подготовка списков оборудования...")

    async with AsyncSessionLocal() as session:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        # noinspection PyTypeChecker
        stmt = select(Order).where(
            Order.order_date.between(today_start, today_end),
            Order.status == OrderStatus.ASSIGNED
        )
        result = await session.execute(stmt)
        orders = result.scalars().all()

        staff_orders = {}
        for o in orders:
            if o.employee_id not in staff_orders:
                staff_orders[o.employee_id] = []
            staff_orders[o.employee_id].append(o)

        for emp_id, items in staff_orders.items():
            user = await session.get(User, emp_id)
            if not user:
                continue

            msg = (
                " *Ваше оборудование на сегодня:*\n\n"
                "🛠 Многоразовое: Пылесос, Пароочиститель, Швабра\n"
                f" Расходники: Тряпки ({len(items) * 2}шт), Перчатки ({len(items)} пары)\n\n"
                " Хорошей смены!"
            )
            try:
                await bot.send_message(user.telegram_id, msg, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Ошибка уведомления сотрудника {emp_id}: {e}")


async def auto_assign_monitor(bot):
    from services.dispatcher import OrderDispatcher

    logger.info("Проверка очереди заказов на просрочку...")

    async with AsyncSessionLocal() as session:
        hour_ago = datetime.now() - timedelta(hours=1)

        # noinspection PyTypeChecker
        stmt = select(Order).where(
            Order.status == OrderStatus.AWAITING,
            Order.created_at <= hour_ago
        )
        result = await session.execute(stmt)
        stale_orders = result.scalars().all()

        if stale_orders:
            dispatcher = OrderDispatcher(bot, session)
            for order in stale_orders:
                logger.info(f"Заказ #{order.id} просрочен. Назначаю автоматически.")
                # Вызываем логику автораспределения по приоритету (ТЗ 4.3)
                await dispatcher.auto_assign_logic(order.id)


def setup_scheduler(bot):
    scheduler = AsyncIOScheduler()

    scheduler.add_job(sync_schedule_task, 'interval', minutes=30)

    scheduler.add_job(auto_assign_monitor, 'interval', minutes=15, args=[bot])

    scheduler.add_job(check_inventory_task, 'interval', hours=6, args=[bot])

    scheduler.add_job(daily_equipment_task, 'cron', hour=9, minute=0, args=[bot])

    scheduler.start()
    logger.info(" Система фоновых задач запущена успешно.")
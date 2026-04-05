import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Router, F, flags
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.requests import get_employee_daily_hours, get_employee_weekly_hours, get_orders_by_status, \
    update_order_status, create_work_slot
from database.models import OrderStatus, UserRole, Order, User as DBUser
from keyboards.staff_kb import accept_order_kb, staff_main_menu
from services.google_sheets import google_sheets
from keyboards.inline import rating_kb

router = Router()


@router.message(F.text == "Новые заказы")
@flags.allowed_roles([UserRole.STAFF, UserRole.ADMIN])
async def new_orders(message: Message, session, user):
    if not user.has_returned_equipment:
        await message.answer("Доступ заблокирован. Пожалуйста, подтвердите сдачу инвентаря за прошлую смену.")
        return
    orders = await get_orders_by_status(session, OrderStatus.AWAITING)
    if not orders:
        await message.answer("На данный момент доступных заказов нет.")
        return
    for order in orders:
        service_name = order.service.name if order.service else (order.custom_details or "Индивидуальный расчет")
        text = (f"Заказ #{order.id}\n\nУслуга: {service_name}\n"
                f"Адрес: {order.address}\nДата: {order.order_date.strftime('%d.%m.%Y %H:%M')}\nСумма: {order.total_price} BYN")
        await message.answer(text, reply_markup=accept_order_kb(order.id))


@router.callback_query(F.data.startswith("accept_"))
@flags.allowed_roles([UserRole.STAFF, UserRole.ADMIN])
async def accept_order(callback: CallbackQuery, session, user):
    order_id = int(callback.data.split("_")[1])
    # noinspection PyTypeChecker
    result = await session.execute(select(Order).options(selectinload(Order.service)).where(Order.id == order_id))
    order = result.scalars().first()

    if order and order.status != OrderStatus.AWAITING:
        await callback.answer("Данный заказ уже принят другим сотрудником.", show_alert=True)
        return

    await update_order_status(session, order_id, OrderStatus.ASSIGNED, user.id)

    duration = order.service.duration_minutes if order.service else 120
    await create_work_slot(session, user.id, order.id, 'travel_to', order.order_date - timedelta(minutes=30),
                           order.order_date)
    await create_work_slot(session, user.id, order.id, 'cleaning', order.order_date,
                           order.order_date + timedelta(minutes=duration))
    await create_work_slot(session, user.id, order.id, 'travel_from', order.order_date + timedelta(minutes=duration),
                           order.order_date + timedelta(minutes=duration + 30))

    user.has_returned_equipment = False
    await session.commit()
    await callback.message.edit_text(f"Заказ #{order_id} успешно принят в работу.")

    client_user = await session.get(DBUser, order.client_id)
    if client_user:
        # noinspection PyBroadException
        try:
            await callback.message.bot.send_message(
                client_user.telegram_id,
                f"Уважаемый клиент! На ваш заказ #{order.id} назначен специалист: {user.full_name}. Ожидайте его в назначенное время."
            )
        except Exception:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("decline_"))
@flags.allowed_roles([UserRole.STAFF, UserRole.ADMIN])
async def decline_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    await callback.message.edit_text(f"Вы отказались от выполнения заказа #{order_id}.")
    await callback.answer()


@router.message(F.text == "Начать работу")
@flags.allowed_roles([UserRole.STAFF, UserRole.ADMIN])
async def start_work(message: Message, session, user):
    # noinspection PyTypeChecker
    query = select(Order).where(Order.employee_id == user.id, Order.status == OrderStatus.ASSIGNED).order_by(
        Order.order_date.asc())
    order = (await session.execute(query)).scalars().first()
    if not order:
        await message.answer("У вас нет назначенных заказов, готовых к выполнению.")
        return
    order.status = OrderStatus.IN_PROGRESS
    await session.commit()
    await message.answer(f"Статус заказа #{order.id} изменен на 'В процессе'.")


@router.message(F.text == "Завершить работу")
@flags.allowed_roles([UserRole.STAFF, UserRole.ADMIN])
async def end_work(message: Message, session, user):
    # noinspection PyTypeChecker
    query = select(Order).options(selectinload(Order.service)).where(Order.employee_id == user.id,
                                                                     Order.status == OrderStatus.IN_PROGRESS)
    order = (await session.execute(query)).scalars().first()
    if not order:
        await message.answer("У вас нет активных заказов в статусе 'В процессе'.")
        return

    order.status = OrderStatus.COMPLETED
    await session.commit()

    service_name = order.service.name if order.service else (order.custom_details or "Индивидуальный расчет")
    report = {'id': order.id, 'date': order.order_date.strftime('%d.%m.%Y'), 'employee_name': user.full_name,
              'service': service_name, 'total_price': order.total_price}
    await asyncio.to_thread(google_sheets.add_order_to_stats, report)
    await asyncio.to_thread(google_sheets.consume_disposable_materials,
                            order.service.category if order.service else "Квартиры")

    await message.answer("Заказ успешно завершен. Пожалуйста, не забудьте сдать инвентарь в конце смены.",
                         reply_markup=staff_main_menu())

    client_user = await session.get(DBUser, order.client_id)
    if client_user:
        try:
            await message.bot.send_message(
                client_user.telegram_id,
                f"Уважаемый клиент! Работы по заказу #{order.id} успешно завершены.\n\nПожалуйста, оцените качество выполненной уборки по 5-балльной шкале:",
                reply_markup=rating_kb(order.id)
            )
        except Exception as e:
            logging.error(f"Review send error: {e}")


@router.message(F.text == "Сдать оборудование")
@flags.allowed_roles([UserRole.STAFF, UserRole.ADMIN])
async def process_return(message: Message, session, user):
    # noinspection PyTypeChecker
    query = select(Order).where(Order.employee_id == user.id, Order.status == OrderStatus.IN_PROGRESS)
    active_order = (await session.execute(query)).scalars().first()
    if active_order:
        await message.answer(
            "Ошибка: Вы не можете сдать инвентарь, пока у вас есть активный заказ в процессе выполнения.")
        return
    user.has_returned_equipment = True
    await session.commit()
    await message.answer("Сдача инвентаря подтверждена. Доступ к новым заказам открыт.")


@router.message(F.text == "Моя статистика")
@flags.allowed_roles([UserRole.STAFF, UserRole.ADMIN])
async def my_stats(message: Message, session, user):
    today = datetime.now()
    daily = await get_employee_daily_hours(session, user.id, today)
    weekly = await get_employee_weekly_hours(session, user.id, today)
    text = (f"Ваша рабочая статистика:\n\nОтработано сегодня (включая дорогу): {daily:.1f} / 10 ч\n"
            f"Отработано за неделю: {weekly:.1f} / 40 ч\n\nДоступно времени на сегодня: {max(0.0, 10.0 - daily):.1f} ч")
    await message.answer(text)


@router.message(F.text == "Мой график")
@flags.allowed_roles([UserRole.STAFF, UserRole.ADMIN])
async def my_schedule(message: Message, user):
    schedule_data = await asyncio.to_thread(google_sheets.get_schedule)
    user_shifts = [s for s in schedule_data if str(s.get('ID сотрудника')) == str(user.telegram_id)]
    if not user_shifts:
        await message.answer(f"График для вашего ID ({user.telegram_id}) не найден в системе.")
        return
    text = "Ваш график работы:\n\n"
    for shift in user_shifts:
        text += f"Дата: {shift.get('Дата')} | Время: {shift.get('Начало работы')} - {shift.get('Конец работы')}\n"
    await message.answer(text)


@router.message(F.text == "Мое оборудование")
@flags.allowed_roles([UserRole.STAFF, UserRole.ADMIN])
async def my_equipment(message: Message, session, user):
    today_start = datetime.now().replace(hour=0, minute=0, second=0)
    today_end = datetime.now().replace(hour=23, minute=59, second=59)
    # noinspection PyTypeChecker
    query = select(Order).where(Order.employee_id == user.id, Order.order_date.between(today_start, today_end))
    orders = (await session.execute(query)).scalars().all()
    if not orders:
        await message.answer("На сегодня у вас нет запланированных заказов.")
        return
    text = "Ваш инвентарь на сегодня:\n\n- Пылесос Karcher\n- Пароочиститель\n- Набор микрофибровых салфеток\n- Профессиональное моющее средство"
    await message.answer(text)
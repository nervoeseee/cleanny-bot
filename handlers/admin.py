import asyncio
import csv
from io import StringIO
from aiogram import Router, F, flags
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, update

from database.requests import get_orders_by_status, get_user_by_telegram_id
from database.models import OrderStatus, Order, User, UserRole
from services.google_sheets import google_sheets
from states.admin import AdminStates
from keyboards.admin_kb import staff_management_kb
from database.models import EquipmentIssue, InventoryItem

router = Router()



@router.message(F.text == "Управление персоналом")
@flags.allowed_roles([UserRole.ADMIN])
async def staff_main_menu_handler(message: Message):
    await message.answer(
        "Раздел управления персоналом. Выберите действие:",
        reply_markup=staff_management_kb()
    )
    return


@router.callback_query(F.data == "staff_list")
async def hr_show_list(callback: CallbackQuery):
    schedule = await asyncio.to_thread(google_sheets.get_schedule)
    if not schedule:
        await callback.answer("Список пуст или таблица недоступна.", show_alert=True)
        return

    text = "Действующий персонал (из реестра Google):\n\n"
    seen = set()
    for s in schedule:
        eid, name = s.get('ID сотрудника'), s.get('ФИО')
        if eid and name and eid not in seen:
            text += f"• ID {eid}: {name}\n"
            seen.add(eid)
    await callback.message.edit_text(text, reply_markup=staff_management_kb())
    return


@router.callback_query(F.data == "staff_add")
async def hr_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.staff_add_name)
    await callback.message.edit_text("Введите полное ФИО нового сотрудника:")
    return


@router.message(AdminStates.staff_add_name)
async def hr_add_name_input(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminStates.staff_add_id)
    await message.answer("Введите Telegram ID сотрудника (число):")
    return


@router.message(AdminStates.staff_add_id)
async def hr_add_final(message: Message, state: FSMContext, session):
    if not message.text.isdigit():
        await message.answer("Ошибка: ID должен быть числом.")
        return

    data = await state.get_data()
    tg_id = int(message.text)
    user = await get_user_by_telegram_id(session, tg_id)
    if user:
        user.role = UserRole.STAFF
    else:
        new_user = User(telegram_id=tg_id, full_name=data['name'], role=UserRole.STAFF)
        session.add(new_user)

    await session.commit()
    await asyncio.to_thread(google_sheets.add_new_staff, tg_id, data['name'])
    await message.answer(f"Сотрудник {data['name']} успешно добавлен в базу и Google Таблицу.")
    await state.clear()
    return


@router.callback_query(F.data == "staff_delete")
async def hr_delete_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.staff_delete_id)
    await callback.message.edit_text("Введите Telegram ID сотрудника для удаления из штата:")
    return


@router.message(AdminStates.staff_delete_id)
async def hr_delete_final(message: Message, state: FSMContext, session):
    if not message.text.isdigit():
        await message.answer("Введите числовой ID.")
        return

    tg_id = int(message.text)
    user = await get_user_by_telegram_id(session, tg_id)
    if user:
        user.role = UserRole.CLIENT
        await session.commit()

    await asyncio.to_thread(google_sheets.remove_staff, tg_id)
    await message.answer(f"Пользователь {tg_id} удален из штата. Доступ к терминалу заблокирован.")
    await state.clear()
    return



@router.message(F.text == "Все заказы")
@flags.allowed_roles([UserRole.ADMIN])
async def all_orders(message: Message, session):
    orders = await get_orders_by_status(session, OrderStatus.AWAITING)
    if not orders:
        await message.answer("Очередь заказов пуста.")
        return

    text = "Заказы, ожидающие назначения:\n\n"
    for order in orders:
        text += f" Заказ #{order.id} | {order.order_date.strftime('%d.%m %H:%M')}\n📍 Адрес: {order.address}\n\n"
    await message.answer(text)
    return


@router.message(F.text == "Жалобы и инциденты")
@flags.allowed_roles([UserRole.ADMIN])
async def show_complaints(message: Message, session):
    # noinspection PyTypeChecker
    result = await session.execute(select(Order).where(Order.complaint == True))
    complaints = result.scalars().all()
    if not complaints:
        await message.answer("Жалоб нет.")
        return

    text = "Список жалоб:\n\n"
    for c in complaints:
        text += f" Заказ #{c.id} | Оценка: {c.rating}/5\n Отзыв: {c.review_text or 'Нет'}\n\n"
    await message.answer(text)
    return


@router.message(F.text == "Статистика")
@flags.allowed_roles([UserRole.ADMIN])
async def show_statistics(message: Message, session):
    # noinspection PyTypeChecker
    res = await session.execute(
        select(func.count(Order.id), func.sum(Order.total_price)).where(Order.status == OrderStatus.COMPLETED)
    )
    data = res.fetchone()
    count, revenue = data[0] or 0, data[1] or 0
    await message.answer(f" Выручка: {revenue:.2f} BYN\n Заказов: {count}")
    return


@router.message(F.text == "Склад")
@flags.allowed_roles([UserRole.ADMIN])
async def show_inventory(message: Message):
    inventory = await asyncio.to_thread(google_sheets.get_inventory)
    text = " Остатки на складе:\n\n"
    for item in inventory:
        text += f"• {item.get('Название')}: {item.get('Остаток')} {item.get('Ед. изм.')}\n"
    await message.answer(text)
    return


@router.message(F.text == "Назначить заказ вручную")
@flags.allowed_roles([UserRole.ADMIN])
async def manual_assign_start(message: Message, state: FSMContext, session):
    orders = await get_orders_by_status(session, OrderStatus.AWAITING)
    if not orders:
        await message.answer("Нет заказов для назначения.")
        return
    await state.set_state(AdminStates.manual_assign)
    await message.answer("Введите ID заказа:")
    return


@router.message(AdminStates.manual_assign)
async def manual_assign_step2(message: Message, state: FSMContext):
    await state.update_data(order_id=int(message.text))
    await state.set_state(AdminStates.select_employee)
    await message.answer("Введите Telegram ID сотрудника из реестра:")
    return


@router.message(AdminStates.select_employee)
async def manual_assign_final(message: Message, state: FSMContext, session):
    data = await state.get_data()
    tg_id = int(message.text)
    user = await get_user_by_telegram_id(session, tg_id)
    if not user:
        await message.answer("Сотрудник не найден в базе.")
        return

    # noinspection PyTypeChecker
    await session.execute(
        update(Order).where(Order.id == data['order_id']).values(
            employee_id=user.id, status=OrderStatus.ASSIGNED
        )
    )
    await session.commit()
    await message.answer(f"Заказ #{data['order_id']} назначен на {user.full_name}")
    await state.clear()
    return


@router.message(F.text == "Выгрузить отчеты")
@flags.allowed_roles([UserRole.ADMIN])
async def export_reports(message: Message, session):
    # noinspection PyTypeChecker
    result = await session.execute(select(Order).where(Order.status == OrderStatus.COMPLETED))
    orders = result.scalars().all()
    if not orders:
        await message.answer("Нет данных.")
        return

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Дата', 'Адрес', 'Сумма', 'Оценка'])
    for o in orders:
        writer.writerow([o.id, o.order_date.strftime('%d.%m.%Y'), o.address, o.total_price, o.rating or '-'])

    csv_file = BufferedInputFile(output.getvalue().encode('utf-8'), filename="report.csv")
    await message.answer_document(csv_file, caption="Отчет сформирован.")
    return
@router.message(F.text == "Разблокировать сотрудника")
@flags.allowed_roles([UserRole.ADMIN])
async def unblock_staff(message: Message, session):
    await message.answer("Введите Telegram ID сотрудника для разблокировки:")

@router.message(F.text == "Зафиксировать поломку")
@flags.allowed_roles([UserRole.ADMIN])
async def report_issue_start(message: Message, state: FSMContext):
    await state.set_state(AdminStates.report_issue_tg_id)
    await message.answer("Введите Telegram ID сотрудника:")

@router.message(AdminStates.report_issue_tg_id)
async def report_issue_id(message: Message, state: FSMContext, session):
    user = await get_user_by_telegram_id(session, int(message.text))
    if not user: return await message.answer("Сотрудник не найден.")
    await state.update_data(emp_id=user.id)
    await state.set_state(AdminStates.report_issue_item)
    await message.answer("Введите название оборудования (как в таблице Склад):")

@router.message(AdminStates.report_issue_item)
async def report_issue_item(message: Message, state: FSMContext, session):
    item = await session.execute(select(InventoryItem).where(InventoryItem.name == message.text))
    item = item.scalar_one_or_none()
    if not item: return await message.answer("Оборудование не найдено.")
    await state.update_data(item_id=item.id)
    await state.set_state(AdminStates.report_issue_desc)
    await message.answer("Опишите поломку/потерю:")

@router.message(AdminStates.report_issue_desc)
async def report_issue_final(message: Message, state: FSMContext, session):
    data = await state.get_data()
    issue = EquipmentIssue(employee_id=data['emp_id'], item_id=data['item_id'],
                           issue_type="damage", description=message.text)
    session.add(issue)
    item = await session.get(InventoryItem, data['item_id'])
    item.quantity -= 1
    await session.commit()
    await message.answer("✅ Инцидент зафиксирован, оборудование списано.")
    await state.clear()
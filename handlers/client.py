import asyncio
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.exceptions import TelegramAPIError

from database.requests import get_services, get_service_by_id, get_public_reviews
from database.models import Order as DBOrder
from keyboards.client_kb import (
    services_kb, calculator_kb, rooms_kb,
    extras_kb, categories_kb, bathrooms_kb, windows_kb
)
from keyboards.inline import (
    back_to_menu_kb, confirmation_kb, payment_kb,
    proceed_to_order_kb
)
from services.calculator_logic import CalculatorService
from services.google_sheets import google_sheets
from states.order_states import OrderForm, CalculatorStates, ReviewStates
import config

router = Router()



@router.message(F.text == "Услуги")
async def show_categories(message: Message):
    await message.answer(
        "Пожалуйста, выберите категорию клининга для ознакомления с перечнем услуг:",
        reply_markup=categories_kb()
    )


@router.callback_query(F.data.startswith("cat_"))
async def show_services_by_category(callback: CallbackQuery, session):
    cb_data = str(callback.data)
    category = cb_data.split("_")[1]
    services = await get_services(session, category=category)

    if not services:
        await callback.answer(f"В категории '{category}' временно нет услуг.", show_alert=True)
        return

    await callback.message.edit_text(
        f"Категория: {category}\nВыберите услугу для получения подробной информации:",
        reply_markup=services_kb(services)
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_categories")
async def back_to_categories_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "Пожалуйста, выберите интересующую вас категорию клининга:",
        reply_markup=categories_kb()
    )
    await callback.answer()


@router.callback_query(StateFilter(None), F.data.startswith("service_"))
async def service_detail(callback: CallbackQuery, session):
    cb_data = str(callback.data)
    service_id = int(cb_data.split("_")[1])
    service = await get_service_by_id(session, service_id)
    if service:
        text = (
            f"Услуга: {service.name}\n\n"
            f"{service.description if service.description else 'Подробности уточняйте у менеджера.'}\n\n"
            f"Базовая стоимость: от {service.base_price} BYN\n"
            f"Расчетное время выполнения: ~{service.duration_minutes} мин\n\n"
            f"Для индивидуального расчета воспользуйтесь инструментом 'Калькулятор стоимости'."
        )
        await callback.message.edit_text(text, reply_markup=back_to_menu_kb())
    await callback.answer()



@router.message(F.text == "Калькулятор стоимости")
async def show_calculator(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Система автоматического расчета стоимости.\nКакой тип расчета вас интересует?",
        reply_markup=calculator_kb()
    )


@router.callback_query(F.data.in_(["calc_quick", "calc_full"]))
async def calc_start(callback: CallbackQuery, state: FSMContext):
    cb_data = str(callback.data)
    calc_type = cb_data.split("_")[1]
    await state.update_data(calc_type=calc_type, extras=[])
    await state.set_state(CalculatorStates.rooms)
    await callback.message.edit_text(
        "Шаг 1 из 4: Укажите количество жилых комнат в помещении:",
        reply_markup=rooms_kb()
    )
    await callback.answer()


@router.callback_query(CalculatorStates.rooms, F.data.startswith("rooms_"))
async def calc_rooms(callback: CallbackQuery, state: FSMContext):
    cb_data = str(callback.data)
    rooms = int(cb_data.split("_")[1])
    await state.update_data(rooms=rooms)
    data = await state.get_data()

    if data['calc_type'] == "quick":
        await state.set_state(CalculatorStates.extras)
        await callback.message.edit_text(
            "Шаг 2 из 2: Выберите необходимые дополнительные опции:",
            reply_markup=extras_kb()
        )
    else:
        await state.set_state(CalculatorStates.bathrooms)
        await callback.message.edit_text(
            "Шаг 2 из 4: Укажите количество санузлов:",
            reply_markup=bathrooms_kb()
        )
    await callback.answer()


@router.callback_query(CalculatorStates.bathrooms, F.data.startswith("bathrooms_"))
async def calc_bathrooms(callback: CallbackQuery, state: FSMContext):
    cb_data = str(callback.data)
    await state.update_data(bathrooms=int(cb_data.split("_")[1]))
    await state.set_state(CalculatorStates.windows)
    await callback.message.edit_text(
        "Шаг 3 из 4: Укажите количество окон для мойки:",
        reply_markup=windows_kb()
    )
    await callback.answer()


@router.callback_query(CalculatorStates.windows, F.data.startswith("win_"))
async def calc_windows(callback: CallbackQuery, state: FSMContext):
    cb_data = str(callback.data)
    await state.update_data(windows=int(cb_data.split("_")[1]))
    await state.set_state(CalculatorStates.extras)
    await callback.message.edit_text(
        "Шаг 4 из 4: Выберите дополнительные услуги и нажмите 'Рассчитать':",
        reply_markup=extras_kb()
    )
    await callback.answer()


@router.callback_query(CalculatorStates.extras, F.data.startswith("extra_"))
async def calc_extras_handler(callback: CallbackQuery, state: FSMContext, session):
    cb_data = str(callback.data)
    data = await state.get_data()
    extras = data.get("extras", [])

    if cb_data == "extra_done":
        calc_service = CalculatorService(session)
        if data['calc_type'] == "full":
            total = await calc_service.full_calculate(data)
        else:
            total = await calc_service.quick_calculate(0, data['rooms'], extras)

        details = (
            f"Комнат: {data['rooms']}\n"
            f"Санузлов: {data.get('bathrooms', 1)}\n"
            f"Окон: {data.get('windows', 0)}\n"
            f"Опции: {', '.join(extras) if extras else 'Не выбраны'}"
        )

        await state.update_data(final_price=total, details=details, is_from_calc=True)

        text = (
            f"Произведен расчет стоимости:\n\n"
            f"{details}\n\n"
            f"Итого к оплате: {total} BYN\n\n"
            f"Желаете забронировать уборку по данным параметрам?"
        )
        await callback.message.edit_text(text, reply_markup=proceed_to_order_kb())
    else:
        ex_key = cb_data.split("_")[1]
        if ex_key not in extras:
            extras.append(ex_key)
            await state.update_data(extras=extras)
            await callback.answer("Услуга добавлена.")
        else:
            await callback.answer("Уже в списке.")
    await callback.answer()



@router.callback_query(F.data == "proceed_to_order")
async def from_calc_to_order(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderForm.select_date)
    await callback.message.edit_text(
        "Приступаем к оформлению заявки.\nУкажите желаемую дату уборки (в формате ДД.ММ.ГГГГ):"
    )
    await callback.answer()


@router.message(F.text == "Оформить заказ")
async def start_order_manual(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(OrderForm.select_service)
    await message.answer(
        "Оформление новой заявки.\nПожалуйста, выберите категорию помещения:",
        reply_markup=categories_kb()
    )


@router.callback_query(OrderForm.select_service, F.data.startswith("service_"))
async def order_manual_service(callback: CallbackQuery, state: FSMContext, session):
    cb_data = str(callback.data)
    sid = int(cb_data.split("_")[1])
    s = await get_service_by_id(session, sid)

    await state.update_data(service_id=sid, final_price=s.base_price, details=s.name, is_from_calc=False)
    await state.set_state(OrderForm.select_date)
    await callback.message.edit_text("Пожалуйста, укажите желаемую дату уборки (ДД.ММ.ГГГГ):")
    await callback.answer()


@router.message(OrderForm.select_date)
async def order_date_input(message: Message, state: FSMContext):
    try:
        d = datetime.strptime(message.text, "%d.%m.%Y")
        if d.date() < datetime.now().date():
            await message.answer(" Указана прошедшая дата. Пожалуйста, введите корректную дату:")
            return
        await state.update_data(order_date=d)
        await state.set_state(OrderForm.select_time)
        await message.answer("Укажите удобное время прибытия специалиста (в формате ЧЧ:ММ):")
    except ValueError:
        await message.answer("Некорректный формат. Используйте ДД.ММ.ГГГГ (пример: 15.05.2026)")


@router.message(OrderForm.select_time)
async def order_time_input(message: Message, state: FSMContext):
    try:
        t = datetime.strptime(message.text, "%H:%M").time()
        if t.hour < 9 or t.hour >= 20:
            await message.answer(" Рабочие часы сервиса с 09:00 до 20:00. Выберите другое время.")
            return

        data = await state.get_data()
        dt = datetime.combine(data['order_date'], t)

        await state.update_data(order_datetime=dt)
        await state.set_state(OrderForm.enter_address)
        await message.answer("Пожалуйста, введите точный адрес объекта (улица, дом, квартира):")
    except ValueError:
        await message.answer(" Некорректный формат. Используйте ЧЧ:ММ (пример: 12:30)")


@router.message(OrderForm.enter_address)
async def order_address_input(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(OrderForm.payment_method)
    await message.answer("Пожалуйста, выберите удобный способ оплаты:", reply_markup=payment_kb())


@router.callback_query(OrderForm.payment_method, F.data.startswith("pay_"))
async def order_payment_handler(callback: CallbackQuery, state: FSMContext):
    cb_data = str(callback.data)
    payment = cb_data.split("_")[1]
    await state.update_data(payment=payment)
    data = await state.get_data()

    text = (
        f"Пожалуйста, подтвердите данные вашей заявки:\n\n"
        f"Детали: {data['details']}\n"
        f"Дата и время: {data['order_datetime'].strftime('%d.%m.%Y %H:%M')}\n"
        f"Адрес: {data['address']}\n"
        f"Способ оплаты: {payment}\n\n"
        f"Итого к оплате: {data['final_price']} BYN\n\n"
        f"Все верно?"
    )
    await state.set_state(OrderForm.confirm)
    await callback.message.edit_text(text, reply_markup=confirmation_kb())
    await callback.answer()


@router.callback_query(OrderForm.confirm, F.data == "confirm_yes")
async def order_finish_handler(callback: CallbackQuery, state: FSMContext, session, user):
    data = await state.get_data()

    new_order = DBOrder(
        client_id=user.id,
        service_id=data.get('service_id'),
        address=data['address'],
        order_date=data['order_datetime'],
        total_price=data['final_price'],
        payment_method=data['payment'],
        custom_details=data['details']
    )
    session.add(new_order)
    await session.commit()
    await session.refresh(new_order)

    await callback.message.edit_text(
        "Благодарим за обращение! Ваша заявка успешно принята. "
        "Система начала поиск подходящего специалиста. Ожидайте уведомления."
    )

    from services.dispatcher import OrderDispatcher
    dispatcher = OrderDispatcher(callback.bot, session)
    await dispatcher.send_offers_to_staff(new_order.id)

    await state.clear()
    await callback.answer()



@router.callback_query(F.data.startswith("rate_"))
async def process_rating_handler(callback: CallbackQuery, state: FSMContext):
    cb_data = str(callback.data)
    parts = cb_data.split("_")
    rating, order_id = int(parts[1]), int(parts[2])

    await state.update_data(review_order_id=order_id, review_rating=rating)
    await state.set_state(ReviewStates.waiting_for_text)

    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить без комментария", callback_data="skip_text")]
    ])

    await callback.message.edit_text(
        f"Вы оценили качество уборки на {rating} из 5 баллов.\n\n"
        "Пожалуйста, оставьте краткий комментарий о работе специалиста. "
        "Это поможет нам повысить уровень сервиса:",
        reply_markup=skip_kb
    )
    await callback.answer()


@router.message(ReviewStates.waiting_for_text)
async def process_review_text_handler(message: Message, state: FSMContext, session):
    data = await state.get_data()
    await finalize_review(session, message.bot, data['review_order_id'], data['review_rating'], message.text)
    await message.answer("Благодарим за обратную связь! Ваше мнение очень важно для нас.")
    await state.clear()


@router.callback_query(F.data == "skip_text")
async def skip_text_handler(callback: CallbackQuery, state: FSMContext, session):
    data = await state.get_data()
    await finalize_review(session, callback.bot, data['review_order_id'], data['review_rating'], None)
    await callback.message.edit_text("Ваша оценка успешно принята. Спасибо за сотрудничество!")
    await state.clear()
    await callback.answer()


async def finalize_review(session, bot, order_id, rating, text):
    order = await session.get(DBOrder, order_id)
    if not order:
        return

    order.rating = rating
    order.review_text = text

    if rating <= 3:
        order.complaint = True
        for admin_id in config.ADMIN_IDS:
            try:
                msg = f" Претензия по заказу #{order_id}. Оценка: {rating}.\nКомментарий: {text if text else 'Отсутствует'}"
                await bot.send_message(admin_id, msg)
            except TelegramAPIError:
                pass

    await session.commit()

    report = {
        'id': order_id, 'date': order.order_date.strftime('%d.%m.%Y'),
        'service': 'Уборка', 'total_price': order.total_price, 'rating': rating
    }
    await asyncio.to_thread(google_sheets.add_order_to_stats, report)


@router.message(F.text == "Отзывы клиентов")
async def show_reviews_handler(message: Message, session):
    reviews = await get_public_reviews(session, limit=5)
    if not reviews:
        await message.answer("На данный момент в нашей базе еще нет опубликованных отзывов.")
        return

    text = "Последние отзывы наших клиентов:\n\n"
    for r in reviews:
        stars = "⭐" * (r.rating if r.rating else 5)
        comment = r.review_text if r.review_text else 'Без комментария.'
        text += f"{stars}\n«{comment}»\n"
        text += "───────────────\n"

    await message.answer(text, reply_markup=back_to_menu_kb())
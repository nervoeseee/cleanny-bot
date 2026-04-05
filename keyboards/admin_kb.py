from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def admin_main_menu():
    buttons = [
        [KeyboardButton(text="Все заказы"), KeyboardButton(text="Жалобы и инциденты")],
        [KeyboardButton(text="Статистика"), KeyboardButton(text="Склад")],
        [KeyboardButton(text="Управление персоналом"), KeyboardButton(text="Выгрузить отчеты")],
        [KeyboardButton(text="Назначить заказ вручную")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Панель управления..."
    )

def staff_management_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Список персонала", callback_data="staff_list")],
        [InlineKeyboardButton(text=" Добавить сотрудника", callback_data="staff_add")],
        [InlineKeyboardButton(text=" Удалить сотрудника", callback_data="staff_delete")],
        [InlineKeyboardButton(text=" Назад", callback_data="back_to_main")]
    ])
    return keyboard
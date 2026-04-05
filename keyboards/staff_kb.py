from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def staff_main_menu():
    buttons = [[KeyboardButton(text="Новые заказы"), KeyboardButton(text="Мое оборудование")],[KeyboardButton(text="Начать работу"), KeyboardButton(text="Завершить работу")],[KeyboardButton(text="Мой график"), KeyboardButton(text="Моя статистика")],
        [KeyboardButton(text="Сдать оборудование")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, input_field_placeholder="Терминал сотрудника...")

def accept_order_kb(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Принять заказ", callback_data=f"accept_{order_id}")],[InlineKeyboardButton(text="Отказаться", callback_data=f"decline_{order_id}")]
    ])
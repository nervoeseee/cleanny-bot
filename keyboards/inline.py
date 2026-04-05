from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def back_to_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад в главное меню", callback_data="back_to_main")]])

def confirmation_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Подтвердить заказ", callback_data="confirm_yes")],[InlineKeyboardButton(text="Отменить", callback_data="back_to_main")]
    ])

def payment_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Наличными", callback_data="pay_Наличными")],[InlineKeyboardButton(text="Картой (терминал)", callback_data="pay_Картой")],[InlineKeyboardButton(text="Онлайн (по ссылке)", callback_data="pay_Онлайн")],[InlineKeyboardButton(text="Отменить оформление", callback_data="back_to_main")]
    ])

def proceed_to_order_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Оформить данный заказ", callback_data="proceed_to_order")],[InlineKeyboardButton(text="Назад в меню", callback_data="back_to_main")]
    ])

def rating_kb(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="1", callback_data=f"rate_1_{order_id}"),
            InlineKeyboardButton(text="2", callback_data=f"rate_2_{order_id}"),
            InlineKeyboardButton(text="3", callback_data=f"rate_3_{order_id}"),
            InlineKeyboardButton(text="4", callback_data=f"rate_4_{order_id}"),
            InlineKeyboardButton(text="5", callback_data=f"rate_5_{order_id}")
        ]
    ])
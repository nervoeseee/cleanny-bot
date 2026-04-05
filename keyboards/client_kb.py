from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb():
    buttons = [[KeyboardButton(text="Услуги")],
        [KeyboardButton(text="Калькулятор стоимости"), KeyboardButton(text="Отзывы клиентов")],
        [KeyboardButton(text="Оформить заказ")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def categories_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Уборка квартир", callback_data="cat_Квартиры")],
        [InlineKeyboardButton(text="Уборка домов", callback_data="cat_Дома")],[InlineKeyboardButton(text="Уборка после ремонта", callback_data="cat_После ремонта")],[InlineKeyboardButton(text="Химчистка мебели", callback_data="cat_Химчистка")],[InlineKeyboardButton(text="Мойка окон", callback_data="cat_Окна")],[InlineKeyboardButton(text="Назад в меню", callback_data="back_to_main")]
    ])

def services_kb(services):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for service in services:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"{service.name} — {service.base_price} BYN", callback_data=f"service_{service.id}")
        ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад к категориям", callback_data="back_to_categories")])
    return keyboard

def calculator_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Краткий расчет", callback_data="calc_quick")],[InlineKeyboardButton(text="Полный расчет", callback_data="calc_full")],[InlineKeyboardButton(text="Назад в меню", callback_data="back_to_main")]
    ])

def rooms_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="1 комната", callback_data="rooms_1"), InlineKeyboardButton(text="2 комнаты", callback_data="rooms_2")],[InlineKeyboardButton(text="3 комнаты", callback_data="rooms_3"), InlineKeyboardButton(text="4+ комнаты", callback_data="rooms_4")],
        [InlineKeyboardButton(text="Отменить", callback_data="back_calc_type")]
    ])

def bathrooms_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="1 санузел", callback_data="bathrooms_1")],[InlineKeyboardButton(text="2 санузла", callback_data="bathrooms_2")],[InlineKeyboardButton(text="3+ санузла", callback_data="bathrooms_3")]
    ])

def windows_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Без окон", callback_data="win_0")],
        [InlineKeyboardButton(text="1-3 окна", callback_data="win_3")],[InlineKeyboardButton(text="4-6 окон", callback_data="win_6")],[InlineKeyboardButton(text="7+ окон", callback_data="win_10")]
    ])

def extras_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Холодильник", callback_data="extra_fridge"), InlineKeyboardButton(text="Духовка", callback_data="extra_oven")],[InlineKeyboardButton(text="Балкон", callback_data="extra_balcony"), InlineKeyboardButton(text="Микроволновка", callback_data="extra_microwave")],[InlineKeyboardButton(text="Рассчитать стоимость", callback_data="extra_done")]
    ])
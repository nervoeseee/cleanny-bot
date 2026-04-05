from aiogram.fsm.state import StatesGroup, State

class StaffAuth(StatesGroup):
    waiting_for_password = State()

class OrderForm(StatesGroup):
    select_service = State()
    select_date = State()
    select_time = State()
    enter_address = State()
    payment_method = State()
    confirm = State()

class CalculatorStates(StatesGroup):
    calc_type = State()
    rooms = State()
    bathrooms = State()
    windows = State()
    extras = State()

class ReviewStates(StatesGroup):
    waiting_for_rating = State()
    waiting_for_text = State()
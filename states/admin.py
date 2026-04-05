from aiogram.fsm.state import StatesGroup, State


class AdminStates(StatesGroup):
    manual_assign = State()
    select_employee = State()
    staff_add_name = State()
    staff_add_id = State()
    staff_delete_id = State()

    report_issue_tg_id = State()
    report_issue_item = State()
    report_issue_desc = State()
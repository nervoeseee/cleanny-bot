from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from database.requests import update_user_role
from database.models import UserRole
from keyboards.client_kb import main_menu_kb
from keyboards.staff_kb import staff_main_menu
from keyboards.admin_kb import admin_main_menu
from states.order_states import StaffAuth
import config

router = Router()

def get_menu_by_role(user):
    if user.is_blocked:
        return "Ваш аккаунт заблокирован администратором.", None

    role = str(user.role.value if hasattr(user.role, 'value') else user.role).lower()

    if "admin" in role:
        return "Авторизация пройдена. Панель управления администратора:", admin_main_menu()
    elif "staff" in role:
        return "Авторизация пройдена. Рабочий терминал сотрудника:", staff_main_menu()
    else:
        return "Добро пожаловать в Cleanny!\nПожалуйста, выберите интересующий вас раздел:", main_menu_kb()

@router.message(CommandStart())
async def cmd_start(message: Message, user, state: FSMContext):
    await state.clear()
    text, kb = get_menu_by_role(user)
    if kb:
        await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text)

@router.message(Command("admin"))
async def cmd_admin(message: Message, user, session, state: FSMContext):
    await state.clear()
    if message.from_user.id in config.ADMIN_IDS:
        await update_user_role(session, user.telegram_id, UserRole.ADMIN)
        await message.answer("Доступ администратора подтвержден.\nИспользуйте /start для обновления интерфейса.")
    else:
        await message.answer("Ошибка доступа. Ваш идентификатор не найден в списке администраторов.")

@router.message(Command("staff"))
async def cmd_staff(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(StaffAuth.waiting_for_password)
    await message.answer("Для входа в рабочий терминал, пожалуйста, введите корпоративный пароль доступа:")

@router.message(StaffAuth.waiting_for_password)
async def check_staff_password(message: Message, user, session, state: FSMContext):
    if message.text == "123456789":
        await update_user_role(session, user.telegram_id, UserRole.STAFF)
        await message.answer("Пароль принят. Режим сотрудника активирован.\nИспользуйте /start для входа в терминал.")
        await state.clear()
    else:
        await message.answer("Неверный пароль доступа. Попробуйте еще раз или используйте /start для возврата в меню клиента.")


@router.message(Command("client"))
async def cmd_client(message: Message, user, session, state: FSMContext):
    await state.clear()
    await update_user_role(session, user.telegram_id, UserRole.CLIENT)
    await message.answer("Режим клиента активирован.\nИспользуйте /start для обновления меню.")


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, user, state: FSMContext):
    await state.clear()
    text, kb = get_menu_by_role(user)
    try:
        await callback.message.delete()
    except Exception:
        pass

    if kb:
        await callback.message.answer(text, reply_markup=kb)
    else:
        await callback.message.answer(text)
    await callback.answer()
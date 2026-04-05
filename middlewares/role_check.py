import inspect
import config
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.dispatcher.flags import get_flag

from database.requests import get_user_by_telegram_id, create_user
from database.models import UserRole, User


class RoleCheckMiddleware(BaseMiddleware):


    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        actual_event = event.message or event.callback_query

        if not actual_event or not actual_event.from_user:
            return await handler(event, data)

        user_id = actual_event.from_user.id
        session = data.get('session')

        user = await get_user_by_telegram_id(session, user_id)

        if not user:
            if user_id in config.ADMIN_IDS:
                user = User(
                    telegram_id=user_id,
                    full_name=actual_event.from_user.full_name,
                    role=UserRole.ADMIN,
                    is_blocked=False
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            else:
                user = await create_user(session, user_id, actual_event.from_user.full_name)

        if user.is_blocked:
            if event.message:
                await event.message.answer("⛔️ Ваш аккаунт заблокирован администратором.")
            return None

        data['user'] = user
        data['user_role'] = user.role

        allowed_roles = get_flag(data, "allowed_roles")
        if allowed_roles:
            if user.role not in allowed_roles:
                if event.message:
                    await event.message.answer("🚫 У вас недостаточно прав.")
                return None

        handler_obj = data.get("handler")
        if handler_obj:
            callback = handler_obj.callback
            signature = inspect.signature(callback)
            filtered_data = {k: v for k, v in data.items() if k in signature.parameters}
            return await handler(event, filtered_data)

        return await handler(event, data)
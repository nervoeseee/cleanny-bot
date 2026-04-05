import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database.engine import AsyncSessionLocal

class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            async with AsyncSessionLocal() as session:
                data['session'] = session
                return await handler(event, data)
        except Exception as e:
            logging.error(f"Database error in middleware: {e}")
            return None
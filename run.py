import asyncio
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from database.engine import engine, Base
from handlers import common, client, staff, admin
from middlewares.db import DbSessionMiddleware
from middlewares.role_check import RoleCheckMiddleware
from services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def init_db():

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("База данных успешно инициализирована")


async def main():

    logger.info(" Запуск Cleanny Bot...")

    await init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default_bot_properties=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    dp = Dispatcher(storage=MemoryStorage())

    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(RoleCheckMiddleware())

    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(staff.router)
    dp.include_router(client.router)

    setup_scheduler(bot)
    logger.info(" Планировщик фоновых задач запущен")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info(" Бот в сети и слушает сервер...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f" Критическая ошибка при работе: {e}")
    finally:
        await bot.session.close()
        logger.info("Бот полностью остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
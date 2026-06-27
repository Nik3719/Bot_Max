from config import BOT_TOKEN

import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.client.default import DefaultConnectionProperties

from db import init_db
from bot.handlers import router as handlers_router
from bot.callbacks import router as callbacks_router
from bot.menu import menu_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info("Бот запускается")
# Библиотека шлет токен в параметрах, а сервер требует его в заголовке Authorization
bot = Bot(
    BOT_TOKEN,
    default_connection=DefaultConnectionProperties(
        headers={"Authorization": BOT_TOKEN}
    ),
)
bot.params.clear()


dp = Dispatcher()
# Подключаем роутеры
dp.include_routers(menu_router, handlers_router, callbacks_router)


async def main():
    logger.info("Инициализация базы данных")
    await init_db()
    logger.info("База данных успешно инициализирована.")

    logger.info("Запуск long-polling бота")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка при работе бота: {e}", exc_info=True)
    finally:
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа завершена (Ctrl+C)")

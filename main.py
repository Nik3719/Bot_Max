from config import BOT_TOKEN

import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.client.default import DefaultConnectionProperties

from db.database import init_db
from bot.handlers import router

logging.basicConfig(level=logging.INFO)

# Библиотека шлет токен в параметрах, а сервер требует его в заголовке Authorization без слова Bearer.
bot = Bot(
    BOT_TOKEN,
    default_connection=DefaultConnectionProperties(
        headers={"Authorization": BOT_TOKEN}
    ),
)
bot.params.clear()


dp = Dispatcher()
dp.include_routers(router)


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

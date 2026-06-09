from config import BOT_TOKEN

import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated
from maxapi.client.default import DefaultConnectionProperties

logging.basicConfig(level=logging.INFO)

# Библиотека шлет токен в параметрах, а сервер требует его в заголовке Authorization без слова Bearer.
bot = Bot(
    BOT_TOKEN,
    default_connection=DefaultConnectionProperties( headers={'Authorization': BOT_TOKEN})
)
bot.params.clear()

dp = Dispatcher()

# Ответ бота при нажатии на кнопку "Начать"
@dp.bot_started()
async def bot_started(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text='Привет! Отправь мне /start'
    )

# Ответ бота на команду /start
@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    await event.message.answer(f"Пример чат-бота для MAX 💙")



async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
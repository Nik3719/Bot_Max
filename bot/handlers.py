from maxapi.types import BotStarted, Command, MessageCreated
from db.database import search_user
from main import dp  # Импортируем диспетчер из главного файла

# Ответ бота при нажатии на кнопку "Начать"
@dp.bot_started()
async def bot_started(event: BotStarted):
    
    await event.bot.send_message(
        chat_id=event.chat_id,
        text='Привет! Отправь мне /start'
        
    )
    is_registered = await search_user(event.user_id)
    
    if is_registered:
        await event.bot.send_message(
            chat_id=event.chat_id,
            text='Вы уже зарегистрированы в системе. Спасибо!'
        )
    else:
        await event.bot.send_message(
            chat_id=event.chat_id,
            text='Ты не зарегистрирован'
        )
        
        await add_user(event.user_id)
    


# Ответ бота на команду /start
@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    await event.message.answer(f"Пример чат-бота для MAX 💙")
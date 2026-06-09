from maxapi.types import BotStarted, Command, MessageCreated
from db.database import search_user, add_user
from maxapi import Router
router = Router()
from bot.states import RegState
from maxapi.context.context import MemoryContext
from bot.validators import validate_name, validate_email, validate_and_clean_phone

@router.bot_started()
async def bot_started(event: BotStarted, context: MemoryContext):
    is_registered = await search_user(event.user.user_id)
    
    if is_registered:
        await event.bot.send_message(
            chat_id=event.chat_id,
            text='👋 Вы уже зарегистрированы в системе. Спасибо!'
        )
    else:
        await event.bot.send_message(
            chat_id=event.chat_id,
            text='👋 Добро пожаловать! Для начала работы необходимо пройти регистрацию.\n\n📋 Введите ваше ФИО (Фамилия Имя Отчество):'
        )
        await context.set_state(RegState.WAIT_NAME)

# шаг 1: Ожидание имени
@router.message_created(RegState.WAIT_NAME)
async def process_name(event: MessageCreated, context: MemoryContext):
    if not validate_name(event.message.text):
        await event.bot.send_message(
            chat_id=event.chat_id,
            text='❌ Некорректное ФИО. Пример: Иванов Иван Иванович'
        )
        return
        
    await context.update_data(full_name=event.message.text)
    
    await event.bot.send_message(
        chat_id=event.chat_id,
        text='📧 Введите ваш адрес электронной почты:'
    )
    await context.set_state(RegState.WAIT_EMAIL)

# шаг 2: Ожидание почты
@router.message_created(RegState.WAIT_EMAIL)
async def process_email(event: MessageCreated, context: MemoryContext):
    if not validate_email(event.message.text):
        await event.bot.send_message(
            chat_id=event.chat_id,
            text='❌ Некорректный email. Пример: ivanov@example.ru'
        )
        return
        
    await context.update_data(email=event.message.text)
    
    await event.bot.send_message(
        chat_id=event.chat_id,
        text='📱 Введите ваш номер телефона:'
    )
    await context.set_state(RegState.WAIT_PHONE)

# шаг 3: Ожидание телефона и сохранение в БД
@router.message_created(RegState.WAIT_PHONE)
async def process_phone(event: MessageCreated, context: MemoryContext):
    cleaned_phone = validate_and_clean_phone(event.message.text)
    if not cleaned_phone:
        await event.bot.send_message(
            chat_id=event.chat_id,
            text='❌ Некорректный номер. Пример: +79001234567'
        )
        return
        
    await context.update_data(phone=cleaned_phone)
    
    # Достаем все собранные данные (ФИО, почта, телефон) из памяти
    user_data = await context.get_data()
    
    # Собираем словарь для нашей функции add_user
    user_dict = {
        "max_user_id": str(event.message.sender.user_id),
        "full_name": user_data["full_name"],
        "email": user_data["email"],
        "phone": user_data["phone"]
    }
    
    # Сохраняем в базу данных
    await add_user(user_dict)
    
    # Очищаем память состояний, так как регистрация закончена
    await context.clear()
    
    await event.bot.send_message(
        chat_id=event.chat_id,
        text='✅ Вы успешно зарегистрированы! Добро пожаловать.'
    )

# Команда /start (как запасной вариант)
@router.message_created(Command('start'))
async def hello(event: MessageCreated):
    await event.message.answer("Пример регистрационного бота 💙")

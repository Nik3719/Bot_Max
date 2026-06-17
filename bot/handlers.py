from maxapi.types import BotStarted, Command, MessageCreated
from db.database import search_user, add_user, is_email_registered, is_phone_registered
from maxapi import Router
import logging


from bot.states import RegState
from maxapi.context.context import MemoryContext
from bot.validators import validate_name, validate_email, validate_and_clean_phone

logger = logging.getLogger(__name__)

router = Router()



@router.bot_started()
async def bot_started(event: BotStarted, context: MemoryContext):
    logger.info(f"Событие bot_started для пользователя {event.user.user_id}")
    is_registered = await search_user(event.user.user_id)

    if is_registered:
        await event.bot.send_message(
            chat_id=event.chat_id, text="👋 Вы уже зарегистрированы в системе. Спасибо!"
        )
    else:
        await event.bot.send_message(
            chat_id=event.chat_id,
            text="👋 Добро пожаловать! Для начала работы необходимо пройти регистрацию.\n\n📋 Введите ваше ФИО (Фамилия Имя Отчество):",
        )
        await context.set_state(RegState.WAIT_NAME)


# шаг 1: Ожидание имени
@router.message_created(RegState.WAIT_NAME)
async def process_name(event: MessageCreated, context: MemoryContext):
    if not validate_name((event.message.body.text or "")):
        await event.message.answer("❌ Некорректное ФИО. Пример: Иванов Иван Иванович")
        return

    await context.update_data(full_name=(event.message.body.text or ""))

    await event.message.answer("📧 Введите ваш адрес электронной почты:")
    await context.set_state(RegState.WAIT_EMAIL)


# шаг 2: Ожидание почты
@router.message_created(RegState.WAIT_EMAIL)
async def process_email(event: MessageCreated, context: MemoryContext):
    email = (event.message.body.text or "")
    if not validate_email(email):
        await event.message.answer("❌ Некорректный email. Пример: ivanov@example.ru")
        return

    if await is_email_registered(email):
        await event.message.answer("❌ Этот email уже зарегистрирован. Пожалуйста, введите другой:")
        return

    await context.update_data(email=email)

    await event.message.answer("📱 Введите ваш номер телефона:")
    await context.set_state(RegState.WAIT_PHONE)


# шаг 3: Ожидание телефона и сохранение в БД
@router.message_created(RegState.WAIT_PHONE)
async def process_phone(event: MessageCreated, context: MemoryContext):
    cleaned_phone = validate_and_clean_phone((event.message.body.text or ""))
    if not cleaned_phone:
        await event.message.answer("❌ Некорректный номер. Пример: +79001234567")
        return

    if await is_phone_registered(cleaned_phone):
        await event.message.answer("❌ Этот номер телефона уже зарегистрирован. Пожалуйста, введите другой:")
        return

    await context.update_data(phone=cleaned_phone)

    # Достаем все собранные данные (ФИО, почта, телефон) из памяти
    user_data = await context.get_data()

    # Собираем словарь для нашей функции add_user
    user_dict = {
        "max_user_id": str(event.message.sender.user_id),
        "full_name": user_data["full_name"],
        "email": user_data["email"],
        "phone": user_data["phone"],
    }

    # Сохраняем в базу данных
    try:
        await add_user(user_dict)
        logger.info(f"Пользователь {event.message.sender.user_id} успешно зарегистрирован")
    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя {event.message.sender.user_id} в БД: {e}")
        await event.message.answer("❌ Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.")
        return

    # Очищаем память состояний, так как регистрация закончена
    # await context.clear()

    await event.message.answer("✅ Вы успешно зарегистрированы! Добро пожаловать.")
    await context.set_state(RegState.CHAT)


# Команда /start
@router.message_created(Command("start"))
async def cmd_start(event: MessageCreated, context: MemoryContext):
    logger.info(f"Пользователь {event.message.sender.user_id} отправил команду /start")
    is_registered = await search_user(event.message.sender.user_id)

    if is_registered:
        await event.message.answer("👋 Вы уже зарегистрированы в системе. Спасибо!")
    else:
        await event.message.answer("👋 Добро пожаловать! Для начала работы необходимо пройти регистрацию.\n\n📋 Введите ваше ФИО (Фамилия Имя Отчество):")
        await context.set_state(RegState.WAIT_NAME)


@router.message_created(RegState.CHAT)
async def process_chat_message(event: MessageCreated, context: MemoryContext):
    messages = context.get("messages", [])
    messages.append({
        "role": "user",
        "content": event.message.body.text
    })
    response = await ask_ollama(messages)
    await event.message.answer(response["message"]["content"])


@router.message_created()
async def process_unregistered(event: MessageCreated, context: MemoryContext):
    await event.message.answer("Вы не зарегистрированы. Напишите /start")

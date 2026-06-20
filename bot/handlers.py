import logging
import config

from maxapi.types import BotStarted, Command, MessageCreated
from maxapi import Router
from maxapi.context.context import MemoryContext

from db import (
    search_user,
    add_user,
    is_email_registered,
    is_phone_registered,
    get_chat_history,
    add_chat_message,
    clear_chat_history,
    get_chat_stats,
)

from bot import (
    RegState,
    validate_name,
    validate_email,
    validate_and_clean_phone,
    ask_ollama,
    build_messages,
)
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
        "max_user_id": event.message.sender.user_id,
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

    await event.message.answer("✅ Регистрация завершена! Теперь задавайте вопросы — отвечу с помощью ИИ 🤖")
    await context.set_state(RegState.CHAT)


@router.message_created(Command("start"))
async def cmd_start(event: MessageCreated, context: MemoryContext):
    logger.info(f"Пользователь {event.message.sender.user_id} отправил команду /start")
    is_registered = await search_user(event.message.sender.user_id)

    if is_registered:
        await event.message.answer("👋 Вы уже зарегистрированы! Просто напишите вопрос — я отвечу с помощью ИИ.")
        await context.set_state(RegState.CHAT)
    else:
        await event.message.answer("👋 Добро пожаловать! Для начала работы необходимо пройти регистрацию.\n\n📋 Введите ваше ФИО (Фамилия Имя Отчество):")
        await context.set_state(RegState.WAIT_NAME)

@router.message_created(RegState.CHAT, Command("help"))
async def cmd_help(event: MessageCreated, context: MemoryContext):
    text = (
        "Доступные команды:\n\n"
        "/start — начало\n"
        "/clear — сброс диалога\n"
        "/history — последние реплики\n"
        "/stats — статистика токенов"
    )
    await event.message.answer(text)


@router.message_created(RegState.CHAT, Command("clear"))
async def cmd_clear(event: MessageCreated, context: MemoryContext):
    
    user_id = event.message.sender.user_id
    await clear_chat_history(user_id) 
    await event.message.answer("🗑️ История диалога очищена. Начинайте новый разговор!")

@router.message_created(RegState.CHAT, Command("history"))
async def cmd_history(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    history = await get_chat_history(user_id, 5)
    if not history:
        await event.message.answer("💬 История пуста. Задайте первый вопрос!")
        return

    formatted_history = "\n".join([f"{message['role']}: {message['content']}" for message in history])
    await event.message.answer(formatted_history)

@router.message_created(RegState.CHAT, Command("stats"))
async def cmd_stats(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    stats = await get_chat_stats(user_id)
    text = (
        f"Ваша статистика:\n"
        f"Сообщений: {stats['total_messages']}\n"
        f"Токенов потрачено: {stats['total_tokens']}\n"
        f"Зарегистрированы: {stats['registered_at']}"
    )
    await event.message.answer(text)

@router.message_created(RegState.CHAT)
async def process_chat_message(event: MessageCreated, context: MemoryContext):
    user_id_int = event.message.sender.user_id
    user_id_str = str(user_id_int)
    user_text = event.message.body.text or ""

    if not user_text:
        return

    is_registered = await search_user(user_id_int)
    if not is_registered:
        await context.clear()
        await event.message.answer("⛔ У вас нет доступа к чату. Пройдите регистрацию — напишите /start")
        return

    history = await get_chat_history(user_id_str, config.CHAT_HISTORY_LIMIT)

    # Формируем контекст
    messages = build_messages(history, user_text)

    # Отправляем запрос в Ollama
    response = await ask_ollama(messages)

    if not response:
        await event.message.answer("⚠️ Не удалось получить ответ от ИИ. Попробуйте позже.")
        return

    if "message" not in response or not response["message"].get("content"):
        await event.message.answer("🤔 Модель вернула пустой ответ. Попробуйте перефразировать вопрос.")
        return

    # Извлекаем данные из ответа
    assistant_text = response["message"]["content"]
    prompt_tokens = response.get("prompt_eval_count", 0)
    completion_tokens = response.get("eval_count", 0)
    duration_ms = response.get("total_duration", 0) // 1000000  # из наносекунд в миллисекунды

    # Сохраняем запрос пользователя в БД
    await add_chat_message(
        max_user_id=user_id_int,
        role="user",
        content=user_text,
        model=config.OLLAMA_MODEL,
        prompt_tokens=prompt_tokens,
        completion_tokens=0,
        duration_ms=0
    )

    # Сохраняем ответ модели в БД
    await add_chat_message(
        max_user_id=user_id_int,
        role="assistant",
        content=assistant_text,
        model=config.OLLAMA_MODEL,
        prompt_tokens=0,
        completion_tokens=completion_tokens,
        duration_ms=duration_ms
    )

    # Отправляем ответ пользователю
    await event.message.answer(assistant_text)



@router.message_created()
async def process_unregistered(event: MessageCreated, context: MemoryContext):
    await event.message.answer("⛔ У вас нет доступа к чату. Пройдите регистрацию — напишите /start")

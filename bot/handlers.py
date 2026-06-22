import logging
import config
from aiolimiter import AsyncLimiter

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

user_rate_limiters: dict[int, AsyncLimiter] = {}



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

async def check_rate_limit(user_id: int) -> bool:
    """Проверяет рейт-лимит для пользователя."""
    if user_id not in user_rate_limiters:
        user_rate_limiters[user_id] = AsyncLimiter(max_rate=1, time_period=3)

    limiter = user_rate_limiters[user_id]
    if not limiter.has_capacity():
        return False

    await limiter.acquire()
    return True


async def send_long_message(event: MessageCreated, text: str, max_len: int = 3000):
    """Отправляет длинное сообщение по частям, если оно превышает лимит."""
    if len(text) <= max_len:
        await event.message.answer(text)
        return

    paragraphs = text.split('\n')
    current_msg = ""
    for p in paragraphs:
        p_len = len(p) + (1 if current_msg else 0)
        
        if len(current_msg) + p_len <= max_len:
            current_msg += ("\n" + p) if current_msg else p
        else:
            if current_msg:
                await event.message.answer(current_msg)
                current_msg = ""
            
            if len(p) > max_len:
                for i in range(0, len(p), max_len):
                    await event.message.answer(p[i : i + max_len])
            else:
                current_msg = p
                
    if current_msg:
        await event.message.answer(current_msg)


@router.message_created(RegState.CHAT)
async def process_chat_message(event: MessageCreated, context: MemoryContext):
    user_id_int = event.message.sender.user_id
    user_text = event.message.body.text or ""

    if not user_text:
        return

    # Проверка анти-спама
    if not await check_rate_limit(user_id_int):
        await event.message.answer("⚠️ Пожалуйста, не отправляйте сообщения так часто. Подождите немного.")
        return

    # Проверка доступа (регистрации)
    is_registered = await search_user(user_id_int)
    if not is_registered:
        await context.clear()
        await event.message.answer("⛔ У вас нет доступа к чату. Пройдите регистрацию — напишите /start")
        return

    # Получение истории и формирование контекста
    history = await get_chat_history(str(user_id_int), config.CHAT_HISTORY_LIMIT)
    messages = build_messages(history, user_text)
    
    # Запрос к нейросети
    response = await ask_ollama(messages)

    if not response:
        await event.message.answer("⚠️ Не удалось получить ответ от ИИ. Попробуйте позже.")
        return

    if "message" not in response or not response["message"].get("content"):
        await event.message.answer("🤔 Модель вернула пустой ответ. Попробуйте перефразировать вопрос.")
        return

    assistant_text = response["message"]["content"]

    # Сохраняем запрос пользователя в БД
    await add_chat_message(
        max_user_id=user_id_int,
        role="user",
        content=user_text,
        model=config.OLLAMA_MODEL,
        prompt_tokens=response.get("prompt_eval_count", 0),
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
        completion_tokens=response.get("eval_count", 0),
        duration_ms=response.get("total_duration", 0) // 1000000
    )

    # Отправляем ответ с учетом лимита на символы
    await send_long_message(event, assistant_text)



@router.message_created()
async def process_unregistered(event: MessageCreated, context: MemoryContext):
    await event.message.answer("⛔ У вас нет доступа к чату. Пройдите регистрацию — напишите /start")

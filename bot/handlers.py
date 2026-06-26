import logging
import asyncio
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
    create_chat,
    get_user_chats,
    get_chat,
    update_chat_title,
    delete_chat,
    get_current_chat_id,
    set_current_chat_id,
    count_user_chats,
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

user_last_message_time: dict[int, float] = {}
user_last_warning_time: dict[int, float] = {}

def generate_auto_title(text: str, max_len: int = 30) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > 20:
        return truncated[:last_space] + '...'
    return truncated + '...'


@router.bot_started()
async def bot_started(event: BotStarted, context: MemoryContext):
    # Чтобы не отправлять два приветствия, оставляем здесь только логирование.
    logger.info(f"Событие bot_started для пользователя {event.user.user_id}")


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
        
        # Создаем первый чат
        chat_id = await create_chat(event.message.sender.user_id)
        if chat_id:
            await context.update_data(current_chat_id=chat_id)

    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя {event.message.sender.user_id} в БД: {e}")
        await event.message.answer("❌ Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.")
        return

    # Очищаем память состояний, так как регистрация закончена
    await context.clear()

    await event.message.answer("✅ Регистрация завершена! Создан ваш первый чат.\nЗадайте вопрос — я отвечу с помощью ИИ 🤖")
    await context.set_state(RegState.CHAT)


@router.message_created(Command("start"))
async def cmd_start(event: MessageCreated, context: MemoryContext):
    logger.info(f"Пользователь {event.message.sender.user_id} отправил команду /start")
    is_registered = await search_user(event.message.sender.user_id)

    if is_registered:
        await context.clear()
        
        user_id = event.message.sender.user_id
        chats = await get_user_chats(user_id)
        current_chat_id = await get_current_chat_id(user_id)
        
        if not current_chat_id and chats:
            current_chat_id = chats[0]['id']
            await set_current_chat_id(user_id, current_chat_id)
        elif not current_chat_id and not chats:
            current_chat_id = await create_chat(user_id)
            
        await event.message.answer("👋 Вы уже зарегистрированы! Просто напишите вопрос — я отвечу с помощью ИИ.")
        await context.set_state(RegState.CHAT)
    else:
        await event.message.answer("👋 Добро пожаловать! Для начала работы необходимо пройти регистрацию.\n\n📋 Введите ваше ФИО (Фамилия Имя Отчество):")
        await context.set_state(RegState.WAIT_NAME)

@router.message_created(RegState.CHAT, Command("help"))
async def cmd_help(event: MessageCreated, context: MemoryContext):
    text = (
        "ℹ️ Доступные команды:\n\n"
        "/newchat — новый чат\n"
        "/chats — список чатов\n"
        "/rename — переименовать текущий чат\n"
        "/delete — удалить текущий чат\n"
        "/clear — очистить историю сообщений текущего чата\n"
        "/history — последние реплики\n"
        "/stats — статистика"
    )
    await event.message.answer(text)

@router.message_created(RegState.CHAT, Command("newchat"))
async def cmd_newchat(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    
    chat_count = await count_user_chats(user_id)
    if chat_count >= config.MAX_CHATS_PER_USER:
        await event.message.answer(f"⚠️ Достигнут лимит в {config.MAX_CHATS_PER_USER} чатов. Удалите старые, чтобы создать новые.")
        return
        
    chat_id = await create_chat(user_id)
    if chat_id:
        await event.message.answer("✅ Новый чат создан. Задайте первый вопрос!")
    else:
        await event.message.answer("❌ Ошибка при создании чата.")

@router.message_created(RegState.CHAT, Command("chats"))
async def cmd_chats(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    chats = await get_user_chats(user_id)
    
    if not chats:
        await event.message.answer("У вас нет активных чатов. Напишите /newchat чтобы создать.")
        return
        
    current_chat_id = await get_current_chat_id(user_id)
    
    text = "Ваши чаты:\n\n"
    for idx, chat in enumerate(chats, start=1):
        marker = "🟢" if chat['id'] == current_chat_id else "⚪"
        text += f"{marker} {idx}. {chat['title']}\n"
        
    text += "\nЧтобы переключиться на другой чат, отправьте номер чата (например: 2)."
    await event.message.answer(text)

@router.message_created(RegState.CHAT, Command("rename"))
async def cmd_rename(event: MessageCreated, context: MemoryContext):
    await event.message.answer("Введите новое название для чата (не более 60 символов):")
    await context.set_state(RegState.WAIT_CHAT_RENAME)

@router.message_created(RegState.WAIT_CHAT_RENAME)
async def process_chat_rename(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    new_title = (event.message.body.text or "").strip()
    
    if not new_title:
        await event.message.answer("Название не может быть пустым. Введите название:")
        return
        
    if len(new_title) > config.CHAT_TITLE_MAX_LEN:
        new_title = new_title[:config.CHAT_TITLE_MAX_LEN-3] + "..."
        
    current_chat_id = await get_current_chat_id(user_id)
    if current_chat_id:
        await update_chat_title(current_chat_id, new_title)
        await event.message.answer(f"✅ Чат переименован в «{new_title}».")
    else:
        await event.message.answer("❌ Активный чат не найден.")
        
    await context.set_state(RegState.CHAT)

@router.message_created(RegState.CHAT, Command("delete"))
async def cmd_delete(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    current_chat_id = await get_current_chat_id(user_id)
    
    if not current_chat_id:
        await event.message.answer("❌ У вас нет активного чата.")
        return
        
    chat = await get_chat(current_chat_id)
    title = chat['title'] if chat else "Неизвестный чат"
    
    await delete_chat(current_chat_id)
    await event.message.answer(f"ℹ️ Чат «{title}» удалён.")
    
    chats = await get_user_chats(user_id)
    if chats:
        new_active = chats[0]
        await set_current_chat_id(user_id, new_active['id'])
        await event.message.answer(f"ℹ️ Переключил на чат «{new_active['title']}».")
    else:
        new_id = await create_chat(user_id)
        if new_id:
            await event.message.answer("ℹ️ Создан новый пустой чат, так как вы удалили последний.")

@router.message_created(RegState.CHAT, Command("clear"))
async def cmd_clear(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    current_chat_id = await get_current_chat_id(user_id)
    if current_chat_id:
        await clear_chat_history(current_chat_id) 
        await event.message.answer("ℹ️ История чата очищена. Начинайте новый разговор!")
    else:
        await event.message.answer("❌ У вас нет активного чата.")

@router.message_created(RegState.CHAT, Command("history"))
async def cmd_history(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    current_chat_id = await get_current_chat_id(user_id)
    if not current_chat_id:
        await event.message.answer("❌ У вас нет активного чата.")
        return
        
    history = await get_chat_history(current_chat_id, 5)
    if not history:
        await event.message.answer("💬 История пуста. Задайте первый вопрос!")
        return

    formatted_history = "\n".join([f"{message['role']}: {message['content']}" for message in history])
    await event.message.answer(formatted_history)

@router.message_created(RegState.CHAT, Command("stats"))
async def cmd_stats(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    current_chat_id = await get_current_chat_id(user_id)
    
    stats = await get_chat_stats(user_id, current_chat_id)
    text = (
        f"ℹ️ Ваша статистика:\n"
        f"• Всего чатов: {stats['total_chats']}\n"
        f"• Сообщений в текущем чате: {stats['current_chat_messages']}\n"
        f"• Всего сообщений: {stats['total_messages']}\n"
        f"• Всего токенов: {stats['total_tokens']}\n"
        f"• Зарегистрированы: {stats['registered_at']}"
    )
    await event.message.answer(text)

async def check_rate_limit(user_id: int, message_timestamp: int) -> tuple[bool, bool]:
    ts_sec = message_timestamp / 1000
    last_time = user_last_message_time.get(user_id, 0)
    
    if ts_sec - last_time < 3:
        last_warning = user_last_warning_time.get(user_id, 0)
        if ts_sec - last_warning >= 5:
            user_last_warning_time[user_id] = ts_sec
            return False, True
        return False, False

    user_last_message_time[user_id] = ts_sec
    return True, False

async def send_long_message(event: MessageCreated, text: str, max_len: int = 3000):
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

async def ensure_registered(event: MessageCreated, user_id: int) -> bool:
    is_registered = await search_user(user_id)
    if not is_registered:
        await event.message.answer("⛔ У вас нет доступа к чату. Пройдите регистрацию — напишите /start")
        return False
    return True

@router.message_created(RegState.CHAT)
async def process_chat_message(event: MessageCreated, context: MemoryContext):
    user_id_int = event.message.sender.user_id
    user_text = event.message.body.text or ""

    if not user_text:
        return

    # Проверка на выбор чата по номеру из списка /chats
    if user_text.isdigit():
        idx = int(user_text)
        chats = await get_user_chats(user_id_int)
        if 1 <= idx <= len(chats):
            selected_chat = chats[idx-1]
            await set_current_chat_id(user_id_int, selected_chat['id'])
            
            # Показать превью
            preview_history = await get_chat_history(selected_chat['id'], config.CHAT_PREVIEW_LINES)
            preview_text = "\n".join([f"ℹ️ {msg['role']}: {msg['content'][:50]}..." for msg in preview_history])
            
            await event.message.answer(f"ℹ️ Переключил на чат «{selected_chat['title']}».\nПоследние сообщения:\n{preview_text}")
            return

    is_allowed, should_warn = await check_rate_limit(user_id_int, event.message.timestamp)
    if not is_allowed:
        if should_warn:
            await event.message.answer("⚠️ Пожалуйста, не отправляйте сообщения так часто. Подождите немного.")
        return

    if not await ensure_registered(event, user_id_int):
        await context.clear()
        return

    # Получаем текущий активный чат
    current_chat_id = await get_current_chat_id(user_id_int)
    if not current_chat_id:
        current_chat_id = await create_chat(user_id_int)
        if not current_chat_id:
            await event.message.answer("❌ Ошибка при создании чата.")
            return

    chat = await get_chat(current_chat_id)
    is_first_message = chat['title'] == 'Новый чат' if chat else False

    history = await get_chat_history(current_chat_id, config.CHAT_HISTORY_LIMIT)
    messages = build_messages(history, user_text)
    
    asyncio.create_task(
        handle_ollama_request(event, user_id_int, current_chat_id, user_text, messages, is_first_message)
    )

async def handle_ollama_request(event: MessageCreated, user_id_int: int, chat_id: int, user_text: str, messages: list, is_first_message: bool):
    try:
        chat_to_action = event.message.recipient.chat_id or user_id_int
        await event.bot.send_action(chat_id=chat_to_action)
    except Exception as e:
        logger.warning(f"Не удалось отправить индикатор 'печатает': {e}")

    try:
        response = await ask_ollama(messages)
    except Exception as e:
        logger.error(f"Ошибка при запросе к Ollama: {e}")
        await event.message.answer("⚠️ Не удалось получить ответ от ИИ из‑за ошибки сервера. Попробуйте позже.")
        return

    if not response or "message" not in response or not response["message"].get("content"):
        await event.message.answer("⚠️ Не удалось получить ответ от ИИ. Попробуйте позже.")
        return

    assistant_text = response["message"]["content"]
    logger.info(f"Ollama ответ получен, длина={len(assistant_text)} символов")

    await add_chat_message(
        chat_id=chat_id,
        max_user_id=user_id_int,
        role="user",
        content=user_text,
        model=config.OLLAMA_MODEL,
        prompt_tokens=response.get("prompt_eval_count", 0),
        completion_tokens=0,
        duration_ms=0
    )

    await add_chat_message(
        chat_id=chat_id,
        max_user_id=user_id_int,
        role="assistant",
        content=assistant_text,
        model=config.OLLAMA_MODEL,
        prompt_tokens=0,
        completion_tokens=response.get("eval_count", 0),
        duration_ms=response.get("total_duration", 0) // 1000000
    )

    if is_first_message:
        new_title = generate_auto_title(user_text, config.AUTO_TITLE_MAX_LEN)
        await update_chat_title(chat_id, new_title)

    await send_long_message(event, assistant_text)


@router.message_created()
async def process_unregistered(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    if await ensure_registered(event, user_id):
        await context.set_state(RegState.CHAT)
        await process_chat_message(event, context)

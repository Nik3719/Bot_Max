import logging
import asyncio
import config
from maxapi.types import BotStarted, Command, MessageCreated
from maxapi import Router
from maxapi.context.context import MemoryContext

from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton

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
from bot.tools import try_create_new_chat, build_chats_keyboard, generate_auto_title, get_main_menu
from bot import texts

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



@router.bot_started()
async def bot_started(event: BotStarted, context: MemoryContext):
    # Чтобы не отправлять два приветствия, оставляем здесь только логирование.
    logger.info(f"Событие bot_started для пользователя {event.user.user_id}")


# шаг 1: Ожидание имени
@router.message_created(RegState.WAIT_NAME)
async def process_name(event: MessageCreated, context: MemoryContext):
    if not validate_name((event.message.body.text or "")):
        await event.message.answer(texts.REG_INVALID_NAME)
        return

    await context.update_data(full_name=(event.message.body.text or ""))

    await event.message.answer(texts.REG_ASK_EMAIL)
    await context.set_state(RegState.WAIT_EMAIL)


# шаг 2: Ожидание почты
@router.message_created(RegState.WAIT_EMAIL)
async def process_email(event: MessageCreated, context: MemoryContext):
    email = (event.message.body.text or "")
    if not validate_email(email):
        await event.message.answer(texts.REG_INVALID_EMAIL)
        return

    if await is_email_registered(email):
        await event.message.answer(texts.REG_EMAIL_EXISTS)
        return

    await context.update_data(email=email)

    await event.message.answer(texts.REG_ASK_PHONE)
    await context.set_state(RegState.WAIT_PHONE)


# шаг 3: Ожидание телефона и сохранение в БД
@router.message_created(RegState.WAIT_PHONE)
async def process_phone(event: MessageCreated, context: MemoryContext):
    cleaned_phone = validate_and_clean_phone((event.message.body.text or ""))
    if not cleaned_phone:
        await event.message.answer(texts.REG_INVALID_PHONE)
        return

    if await is_phone_registered(cleaned_phone):
        await event.message.answer(texts.REG_PHONE_EXISTS)
        return

    await context.update_data(phone=cleaned_phone)

    user_data = await context.get_data()
    user_dict = {
        "max_user_id": event.message.sender.user_id,
        "full_name": user_data["full_name"],
        "email": user_data["email"],
        "phone": user_data["phone"],
    }

    try:
        await add_user(user_dict)
        logger.info(f"Пользователь {event.message.sender.user_id} успешно зарегистрирован")
        chat_id = await create_chat(event.message.sender.user_id)
        if chat_id:
            await context.update_data(current_chat_id=chat_id)

    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя {event.message.sender.user_id} в БД: {e}")
        await event.message.answer(texts.REG_ERROR)
        return

    # Сбрасываем состояние после успешной регистрации
    await context.clear()

    await event.message.answer(texts.REG_SUCCESS)
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
            
        await event.message.answer(
            texts.REG_ALREADY,
            attachments=[get_main_menu()]
        )
        await context.set_state(RegState.CHAT)
    else:
        await event.message.answer(texts.REG_WELCOME)
        await context.set_state(RegState.WAIT_NAME)

@router.message_created(RegState.CHAT, Command("help"))
async def cmd_help(event: MessageCreated, context: MemoryContext):
    await event.message.answer(texts.CMD_HELP, attachments=[get_main_menu()])

@router.message_created(RegState.CHAT, Command("newchat"))
async def cmd_newchat(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    success, msg = await try_create_new_chat(user_id)
    await event.message.answer(msg)

@router.message_created(RegState.CHAT, Command("chats"))
async def cmd_chats(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    chats = await get_user_chats(user_id)
    
    if not chats:
        await event.message.answer(texts.CHAT_NO_ANY)
        return
        
    current_chat_id = await get_current_chat_id(user_id)
    markup = build_chats_keyboard(chats, current_chat_id)
    await event.message.answer(texts.CHATS_LIST, attachments=[markup])

@router.message_created(RegState.CHAT, Command("rename"))
async def cmd_rename(event: MessageCreated, context: MemoryContext):
    await event.message.answer(texts.CHAT_RENAME_PROMPT)
    await context.set_state(RegState.WAIT_CHAT_RENAME)

@router.message_created(RegState.WAIT_CHAT_RENAME)
async def process_chat_rename(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    new_title = (event.message.body.text or "").strip()
    
    if not new_title:
        await event.message.answer(texts.CHAT_RENAME_EMPTY)
        return
        
    if len(new_title) > config.CHAT_TITLE_MAX_LEN:
        new_title = new_title[:config.CHAT_TITLE_MAX_LEN-3] + "..."
        
    current_chat_id = await get_current_chat_id(user_id)
    if current_chat_id:
        await update_chat_title(current_chat_id, new_title)
        await event.message.answer(texts.chat_renamed(new_title))
    else:
        await event.message.answer(texts.CHAT_NOT_FOUND)
        
    await context.set_state(RegState.CHAT)

@router.message_created(RegState.CHAT, Command("delete"))
async def cmd_delete(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    current_chat_id = await get_current_chat_id(user_id)
    
    if not current_chat_id:
        await event.message.answer(texts.CHAT_NO_ACTIVE)
        return
        
    chat = await get_chat(current_chat_id)
    title = chat['title'] if chat else "Неизвестный чат"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text=texts.BTN_CONFIRM_DELETE, payload="confirm_delete"),
        CallbackButton(text=texts.BTN_CANCEL, payload="cancel_delete")
    )
    markup = builder.as_markup()
    
    await event.message.answer(texts.chat_delete_confirm(title), attachments=[markup])

@router.message_created(RegState.CHAT, Command("clear"))
async def cmd_clear(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    current_chat_id = await get_current_chat_id(user_id)
    if current_chat_id:
        await clear_chat_history(current_chat_id) 
        await event.message.answer(texts.CHAT_CLEARED)
    else:
        await event.message.answer(texts.CHAT_NO_ACTIVE)

@router.message_created(RegState.CHAT, Command("history"))
async def cmd_history(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    current_chat_id = await get_current_chat_id(user_id)
    if not current_chat_id:
        await event.message.answer(texts.CHAT_NO_ACTIVE)
        return
        
    history = await get_chat_history(current_chat_id, 5)
    if not history:
        await event.message.answer(texts.CHAT_HISTORY_EMPTY)
        return

    formatted_history = "\n".join([f"{message['role']}: {message['content']}" for message in history])
    await event.message.answer(formatted_history)

@router.message_created(RegState.CHAT, Command("stats"))
async def cmd_stats(event: MessageCreated, context: MemoryContext):
    user_id = event.message.sender.user_id
    current_chat_id = await get_current_chat_id(user_id)
    
    stats = await get_chat_stats(user_id, current_chat_id)
    await event.message.answer(texts.chat_stats(stats))

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
        await event.message.answer(texts.ACCESS_DENIED)
        return False
    return True

@router.message_created(RegState.CHAT)
async def process_chat_message(event: MessageCreated, context: MemoryContext):
    user_id_int = event.message.sender.user_id
    user_text = event.message.body.text or ""

    if not user_text:
        return

    if user_text.startswith('/'):
        logger.info(f"Неизвестная команда: {repr(user_text)}")
        await event.message.answer(texts.UNKNOWN_CMD)
        return

    is_allowed, should_warn = await check_rate_limit(user_id_int, event.message.timestamp)
    if not is_allowed:
        if should_warn:
            await event.message.answer(texts.SPAM_WARNING)
        return

    if not await ensure_registered(event, user_id_int):
        await context.clear()
        return

    current_chat_id = await get_current_chat_id(user_id_int)
    if not current_chat_id:
        chat_count = await count_user_chats(user_id_int)
        if chat_count >= config.MAX_CHATS_PER_USER:
            await event.message.answer(texts.chat_limit_reached_auto(config.MAX_CHATS_PER_USER))
            return

        current_chat_id = await create_chat(user_id_int)
        if not current_chat_id:
            await event.message.answer(texts.CHAT_CREATE_ERROR)
            return

    chat = await get_chat(current_chat_id)
    is_first_message = (chat['title'] == 'Новый чат') if chat else False

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
        await event.message.answer(texts.AI_ERROR_SERVER)
        return

    if not response or "message" not in response or not response["message"].get("content"):
        await event.message.answer(texts.AI_ERROR)
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
        
        user_text = event.message.body.text or ""
        if user_text.startswith('/'):
            cmd = user_text.split()[0]
            
            command_handlers = {
                '/help': cmd_help,
                '/newchat': cmd_newchat,
                '/chats': cmd_chats,
                '/rename': cmd_rename,
                '/delete': cmd_delete,
                '/clear': cmd_clear,
                '/history': cmd_history,
                '/stats': cmd_stats,
            }
            
            handler = command_handlers.get(cmd)
            if handler:
                await handler(event, context)
            else:
                logger.info(f"Неизвестная команда (состояние восстановлено): {repr(user_text)}")
                await event.message.answer(texts.UNKNOWN_CMD)
        else:
            await process_chat_message(event, context)

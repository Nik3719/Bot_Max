import logging
import config
from magic_filter import F
from maxapi import Router
from maxapi.context.context import MemoryContext
from maxapi.types.updates.message_callback import MessageCallback

from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton

from db import (
    get_user_chats,
    set_current_chat_id,
    delete_chat,
    create_chat,
    get_chat,
    get_chat_history,
    get_current_chat_id,
)
from bot.tools import try_create_new_chat, build_chats_keyboard

from bot import texts

logger = logging.getLogger(__name__)

router = Router()

@router.message_callback(F.callback.payload.startswith("switch_chat_"))
async def process_switch_chat(event: MessageCallback, context: MemoryContext):
    payload = event.callback.payload
    user_id = event.callback.user.user_id

    try:
        chat_id = int(payload.split("_")[2])
        chats = await get_user_chats(user_id)
        
        # Проверяем, что чат принадлежит пользователю
        if any(c['id'] == chat_id for c in chats):
            await set_current_chat_id(user_id, chat_id)
            chat = await get_chat(chat_id)
            
            preview_history = await get_chat_history(chat_id, config.CHAT_PREVIEW_LINES)
            preview_text = "\n".join([f"ℹ️ {msg['role']}: {msg['content'][:50]}..." if len(msg['content']) > 50 else f"ℹ️ {msg['role']}: {msg['content']}" for msg in preview_history])
            
            text = texts.chat_switched(chat["title"])
            if preview_text:
                text += texts.LAST_MESSAGES_HEADER + preview_text
                
            await event.message.delete()
            await event.message.answer(text=text)
            await event.answer(notification=texts.NOTIFY_CHAT_SWITCHED)
        else:
            await event.answer(notification=texts.CHAT_SWITCH_ERROR)

    except Exception as e:
        logger.error(f"Ошибка при переключении чата {payload}: {e}")
        await event.answer(notification=texts.GENERAL_ERROR)


@router.message_callback(F.callback.payload == "new_chat")
async def process_new_chat(event: MessageCallback, context: MemoryContext):
    user_id = event.callback.user.user_id

    try:
        success, msg = await try_create_new_chat(user_id)
        if success:
            await event.message.delete()
            await event.message.answer(msg)
            await event.answer(notification=texts.NOTIFY_CHAT_CREATED)
        else:
            await event.answer(notification=msg)

    except Exception as e:
        logger.error(f"Ошибка при создании нового чата: {e}")
        await event.answer(notification=texts.GENERAL_ERROR)


@router.message_callback(F.callback.payload == "confirm_delete")
async def process_confirm_delete(event: MessageCallback, context: MemoryContext):
    user_id = event.callback.user.user_id

    try:
        await event.message.delete()
        
        current_chat_id = await get_current_chat_id(user_id)

        if current_chat_id:
            chat = await get_chat(current_chat_id)
            title = chat['title'] if chat else texts.UNKNOWN_CHAT_TITLE

            await delete_chat(current_chat_id)
            await set_current_chat_id(user_id, None)

            chats = await get_user_chats(user_id)

            if not chats:
                new_id = await create_chat(user_id)
                await set_current_chat_id(user_id, new_id)
                await event.message.answer(texts.chat_deleted_last(title))
                await event.message.answer(texts.CHAT_NEW_SUCCESS)
            else:
                markup = build_chats_keyboard(chats, current_chat_id=None)
                await event.message.answer(
                    text=texts.chat_deleted(title),
                    attachments=[markup]
                )

            await event.answer(notification=texts.NOTIFY_CHAT_DELETED)
        else:
            await event.answer(notification=texts.CHAT_NOT_FOUND)

    except Exception as e:
        logger.error(f"Ошибка при удалении чата: {e}")
        await event.answer(notification=texts.GENERAL_ERROR)


@router.message_callback(F.callback.payload == "cancel_delete")
async def process_cancel_delete(event: MessageCallback, context: MemoryContext):
    try:
        await event.message.delete()
        await event.answer(notification=texts.CHAT_DELETE_CANCELLED)
    except Exception as e:
        logger.error(f"Ошибка при отмене удаления: {e}")
        await event.answer(notification=texts.GENERAL_ERROR)


@router.message_callback()
async def process_unknown_callback(event: MessageCallback, context: MemoryContext):
    logger.warning(f"Получен неизвестный callback: {event.callback.payload}")
    await event.answer(notification=texts.UNKNOWN_ACTION)

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
)
from bot.tools import try_create_new_chat, build_chats_keyboard

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
            
            text = f"ℹ️ Вы переключились на чат «{chat['title']}»."
            if preview_text:
                text += f"\nПоследние сообщения:\n{preview_text}"
                
            await event.message.delete()
            await event.message.answer(text=text)
            await event.answer(notification="Чат изменён!")
        else:
            await event.answer(notification="Ошибка: чат не найден или вам не принадлежит.")

    except Exception as e:
        logger.error(f"Ошибка при переключении чата {payload}: {e}")
        await event.answer(notification="Произошла ошибка при выполнении действия.")


@router.message_callback(F.callback.payload == "new_chat")
async def process_new_chat(event: MessageCallback, context: MemoryContext):
    user_id = event.callback.user.user_id

    try:
        success, msg = await try_create_new_chat(user_id)
        if success:
            await event.message.delete()
            await event.message.answer(msg)
            await event.answer(notification="Новый чат создан!")
        else:
            await event.answer(notification=msg)

    except Exception as e:
        logger.error(f"Ошибка при создании нового чата: {e}")
        await event.answer(notification="Произошла ошибка при выполнении действия.")


@router.message_callback(F.callback.payload == "confirm_delete")
async def process_confirm_delete(event: MessageCallback, context: MemoryContext):
    user_id = event.callback.user.user_id

    try:
        await event.message.delete()
        
        from db.database import get_current_chat_id
        current_chat_id = await get_current_chat_id(user_id)
        
        if current_chat_id:
            chat = await get_chat(current_chat_id)
            title = chat['title'] if chat else "Неизвестный чат"
            
            await delete_chat(current_chat_id)
            await set_current_chat_id(user_id, None)
            
            chats = await get_user_chats(user_id)
            markup = build_chats_keyboard(chats, current_chat_id=None)
            
            await event.message.answer(
                text=f"ℹ️ Чат «{title}» удалён.\n\nПожалуйста, выберите другой чат:", 
                attachments=[markup]
            )
            await event.answer(notification="Чат удалён")
        else:
            await event.answer(notification="Активный чат не найден.")

    except Exception as e:
        logger.error(f"Ошибка при удалении чата: {e}")
        await event.answer(notification="Произошла ошибка при выполнении действия.")


@router.message_callback(F.callback.payload == "cancel_delete")
async def process_cancel_delete(event: MessageCallback, context: MemoryContext):
    try:
        await event.message.delete()
        await event.answer(notification="Действие отменено.")
    except Exception as e:
        logger.error(f"Ошибка при отмене удаления: {e}")
        await event.answer(notification="Произошла ошибка.")


@router.message_callback()
async def process_unknown_callback(event: MessageCallback, context: MemoryContext):
    logger.warning(f"Получен неизвестный callback: {event.callback.payload}")
    await event.answer(notification="Неизвестное действие.")

import logging
import config
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
    count_user_chats,
)

logger = logging.getLogger(__name__)

router = Router()

@router.message_callback()
async def process_callbacks(event: MessageCallback, context: MemoryContext):
    payload = event.callback.payload
    if not payload:
        await event.answer()
        return

    user_id = event.callback.user.user_id

    try:
        # 1. Переключение чатов
        if payload.startswith("switch_chat_"):
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

        # 2. Создание нового чата
        elif payload == "new_chat":
            chat_count = await count_user_chats(user_id)
            if chat_count >= config.MAX_CHATS_PER_USER:
                await event.answer(notification=f"Достигнут лимит в {config.MAX_CHATS_PER_USER} чатов.")
                return
                
            new_chat_id = await create_chat(user_id)
            if new_chat_id:
                await event.message.delete()
                await event.message.answer("✅ Новый чат создан. Задайте первый вопрос!")
                await event.answer(notification="Новый чат создан!")
            else:
                await event.answer(notification="Ошибка при создании чата.")

        # 3. Подтверждение удаления
        elif payload == "confirm_delete":
            # Узнаем текущий активный чат перед удалением
            # В данном случае, мы удаляем чат, из которого была вызвана команда /delete
            # (Команда /delete всегда работает с текущим активным)
            
            # Удаляем сам блок с кнопками
            await event.message.delete()
            
            from db.database import get_current_chat_id
            current_chat_id = await get_current_chat_id(user_id)
            
            if current_chat_id:
                chat = await get_chat(current_chat_id)
                title = chat['title'] if chat else "Неизвестный чат"
                
                await delete_chat(current_chat_id)
                
                chats = await get_user_chats(user_id)
                if chats:
                    new_active = chats[0]
                    await set_current_chat_id(user_id, new_active['id'])
                    msg_text = f"ℹ️ Чат «{title}» удалён.\nПереключил на чат «{new_active['title']}»."
                else:
                    new_id = await create_chat(user_id)
                    msg_text = f"ℹ️ Чат «{title}» удалён.\nСоздан новый пустой чат."
                    
                await event.message.answer(text=msg_text)
                await event.answer(notification="Чат удалён")
            else:
                await event.answer(notification="Активный чат не найден.")

        # 4. Отмена удаления
        elif payload == "cancel_delete":
            await event.message.delete() # Удаляем сообщение с кнопками подтверждения
            await event.answer(notification="Действие отменено.")

        else:
            await event.answer()

    except Exception as e:
        logger.error(f"Ошибка при обработке callback {payload}: {e}")
        await event.answer(notification="Произошла ошибка при выполнении действия.")

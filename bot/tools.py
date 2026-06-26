from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton
from db import count_user_chats, create_chat
import config

async def try_create_new_chat(user_id: int) -> tuple[bool, str]:
    """
    Пытается создать новый чат.
    Возвращает (успех, текст_сообщения).
    """
    chat_count = await count_user_chats(user_id)
    if chat_count >= config.MAX_CHATS_PER_USER:
        return False, f"⚠️ Достигнут лимит в {config.MAX_CHATS_PER_USER} чатов. Удалите старые, чтобы создать новые."
        
    chat_id = await create_chat(user_id)
    if chat_id:
        msg = "✅ Новый чат создан. Задайте первый вопрос!"
        if chat_count + 1 >= 45:
            msg += f"\n\n⚠️ У вас уже {chat_count + 1} чатов. Близок лимит ({config.MAX_CHATS_PER_USER}). Рекомендуем удалить ненужные."
        return True, msg
    else:
        return False, "❌ Ошибка при создании чата."

def build_chats_keyboard(chats: list, current_chat_id: int) -> list:
    """
    Строит inline-клавиатуру со списком чатов.
    """
    builder = InlineKeyboardBuilder()
    for chat in chats:
        marker = "🟢" if chat['id'] == current_chat_id else "⚪"
        btn_text = f"{marker} {chat['title']}"
        builder.row(CallbackButton(text=btn_text, payload=f"switch_chat_{chat['id']}"))
        
    builder.row(CallbackButton(text="➕ Создать новый чат", payload="new_chat"))
    return builder.as_markup()

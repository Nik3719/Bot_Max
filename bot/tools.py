from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton, MessageButton
from db import count_user_chats, create_chat
import config
from bot import texts

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        MessageButton(text=texts.BTN_NEW_CHAT),
        MessageButton(text=texts.BTN_CHATS)
    )
    builder.row(
        MessageButton(text=texts.BTN_HISTORY),
        MessageButton(text=texts.BTN_CLEAR)
    )
    builder.row(
        MessageButton(text=texts.BTN_DELETE),
        MessageButton(text=texts.BTN_STATS)
    )
    builder.row(
        MessageButton(text=texts.BTN_HELP)
    )
    return builder.as_markup()

async def try_create_new_chat(user_id: int) -> tuple[bool, str]:
    """
    Пытается создать новый чат.
    Возвращает (успех, текст_сообщения).
    """
    chat_count = await count_user_chats(user_id)
    if chat_count >= config.MAX_CHATS_PER_USER:
        return False, texts.chat_limit_reached(config.MAX_CHATS_PER_USER)
        
    chat_id = await create_chat(user_id)
    if chat_id:
        msg = texts.CHAT_NEW_SUCCESS
        if chat_count + 1 >= 45:
            msg += "\n\n" + texts.chat_limit_warning(config.MAX_CHATS_PER_USER, chat_count + 1)
        return True, msg
    else:
        return False, texts.CHAT_CREATE_ERROR

def build_chats_keyboard(chats: list, current_chat_id: int) -> list:
    """
    Строит inline-клавиатуру со списком чатов.
    """
    builder = InlineKeyboardBuilder()
    for chat in chats:
        marker = "🟢" if chat['id'] == current_chat_id else "⚪"
        btn_text = f"{marker} {chat['title']}"
        builder.row(CallbackButton(text=btn_text, payload=f"switch_chat_{chat['id']}"))
        
    builder.row(CallbackButton(text=texts.BTN_CREATE_NEW_CHAT, payload="new_chat"))
    return builder.as_markup()

def generate_auto_title(text: str, max_len: int = 30) -> str:
    """
    Генерирует короткое название для чата на основе текста первого сообщения.
    """
    text = text.strip()
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > 20:
        return truncated[:last_space] + '...'
    return truncated + '...'

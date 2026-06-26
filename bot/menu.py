from maxapi import Router
from maxapi.context.context import MemoryContext
from maxapi.types.updates.message_created import MessageCreated
from magic_filter import F
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import MessageButton

menu_router = Router()

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        MessageButton(text="Новый чат"),
        MessageButton(text="Мои чаты")
    )
    builder.row(
        MessageButton(text="История"),
        MessageButton(text="Очистить")
    )
    builder.row(
        MessageButton(text="Удалить чат"),
        MessageButton(text="Статистика")
    )
    builder.row(
        MessageButton(text="Помощь")
    )
    return builder.as_markup()

@menu_router.message_created(F.message.body.text == "Новый чат")
async def menu_newchat(event: MessageCreated, context: MemoryContext):
    from bot.handlers import cmd_newchat
    await cmd_newchat(event, context)

@menu_router.message_created(F.message.body.text == "Мои чаты")
async def menu_chats(event: MessageCreated, context: MemoryContext):
    from bot.handlers import cmd_chats
    await cmd_chats(event, context)

@menu_router.message_created(F.message.body.text == "История")
async def menu_history(event: MessageCreated, context: MemoryContext):
    from bot.handlers import cmd_history
    await cmd_history(event, context)

@menu_router.message_created(F.message.body.text == "Очистить")
async def menu_clear(event: MessageCreated, context: MemoryContext):
    from bot.handlers import cmd_clear
    await cmd_clear(event, context)

@menu_router.message_created(F.message.body.text == "Удалить чат")
async def menu_delete(event: MessageCreated, context: MemoryContext):
    from bot.handlers import cmd_delete
    await cmd_delete(event, context)

@menu_router.message_created(F.message.body.text == "Статистика")
async def menu_stats(event: MessageCreated, context: MemoryContext):
    from bot.handlers import cmd_stats
    await cmd_stats(event, context)

@menu_router.message_created(F.message.body.text == "Помощь")
async def menu_help(event: MessageCreated, context: MemoryContext):
    from bot.handlers import cmd_help
    await cmd_help(event, context)

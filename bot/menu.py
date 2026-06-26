from maxapi import Router
from maxapi.context.context import MemoryContext
from maxapi.types.updates.message_created import MessageCreated
from magic_filter import F
from bot import texts

menu_router = Router()

from bot.handlers import (
    cmd_newchat,
    cmd_chats,
    cmd_history,
    cmd_clear,
    cmd_delete,
    cmd_stats,
    cmd_help
)

@menu_router.message_created(F.message.body.text == texts.BTN_NEW_CHAT)
async def menu_newchat(event: MessageCreated, context: MemoryContext):
    await cmd_newchat(event, context)

@menu_router.message_created(F.message.body.text == texts.BTN_CHATS)
async def menu_chats(event: MessageCreated, context: MemoryContext):
    await cmd_chats(event, context)

@menu_router.message_created(F.message.body.text == texts.BTN_HISTORY)
async def menu_history(event: MessageCreated, context: MemoryContext):
    await cmd_history(event, context)

@menu_router.message_created(F.message.body.text == texts.BTN_CLEAR)
async def menu_clear(event: MessageCreated, context: MemoryContext):
    await cmd_clear(event, context)

@menu_router.message_created(F.message.body.text == texts.BTN_DELETE)
async def menu_delete(event: MessageCreated, context: MemoryContext):
    await cmd_delete(event, context)

@menu_router.message_created(F.message.body.text == texts.BTN_STATS)
async def menu_stats(event: MessageCreated, context: MemoryContext):
    await cmd_stats(event, context)

@menu_router.message_created(F.message.body.text == texts.BTN_HELP)
async def menu_help(event: MessageCreated, context: MemoryContext):
    await cmd_help(event, context)

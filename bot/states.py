from maxapi.context.state_machine import State, StatesGroup


class RegState(StatesGroup):
    WAIT_NAME = State()
    WAIT_EMAIL = State()
    WAIT_PHONE = State()
    CHAT = State()
    WAIT_CHAT_RENAME = State()

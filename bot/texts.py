# Регистрация (bot.handlers)
REG_WELCOME = "Добро пожаловать! Для начала работы необходимо пройти регистрацию.\n\nВведите ваше ФИО (Фамилия Имя Отчество):"
REG_INVALID_NAME = "Некорректное ФИО. Пример: Иванов Иван Иванович"
REG_ASK_EMAIL = "📧 Введите ваш адрес электронной почты:"
REG_INVALID_EMAIL = "Некорректный email. Пример: ivanov@example.ru"
REG_EMAIL_EXISTS = "Этот email уже зарегистрирован. Пожалуйста, введите другой:"
REG_ASK_PHONE = "📱 Введите ваш номер телефона:"
REG_INVALID_PHONE = "Некорректный номер. Пример: +79001234567"
REG_PHONE_EXISTS = "Этот номер телефона уже зарегистрирован. Пожалуйста, введите другой:"
REG_ERROR = "Произошла ошибка при регистрации. Пожалуйста, попробуйте позже."
REG_SUCCESS = "✅ Регистрация завершена! Создан ваш первый чат.\nЗадайте вопрос — я отвечу с помощью ИИ 🤖"
REG_ALREADY = "Вы уже зарегистрированы! Просто напишите вопрос — я отвечу с помощью ИИ."

# Ошибки и ограничения (bot.handlers, bot.callbacks)
ACCESS_DENIED = "⛔ У вас нет доступа к чату. Пройдите регистрацию — напишите /start"
UNKNOWN_CMD = "Неизвестная команда или опечатка. Введите /help для списка доступных команд."
UNKNOWN_ACTION = "Неизвестное действие."
SPAM_WARNING = "Пожалуйста, не отправляйте сообщения так часто. Подождите немного."
AI_ERROR_SERVER = "Не удалось получить ответ от ИИ из‑за ошибки сервера. Попробуйте позже."
AI_ERROR = "Не удалось получить ответ от ИИ. Попробуйте позже."
GENERAL_ERROR = "Произошла ошибка при выполнении действия."

# Уведомления (bot.callbacks)
NOTIFY_CHAT_SWITCHED = "Чат изменён!"
NOTIFY_CHAT_CREATED = "Новый чат создан!"
NOTIFY_CHAT_DELETED = "Чат удалён!"
UNKNOWN_CHAT_TITLE = "Неизвестный чат"
LAST_MESSAGES_HEADER = "\nПоследние сообщения:\n"

# Управление чатами (Кнопки) (bot.menu, bot.tools)
BTN_NEW_CHAT = "Новый чат"
BTN_CHATS = "Мои чаты"
BTN_HISTORY = "История"
BTN_CLEAR = "Очистить"
BTN_DELETE = "Удалить чат"
BTN_STATS = "Статистика"
BTN_HELP = "Помощь"
BTN_CREATE_NEW_CHAT = "➕ Создать новый чат"
BTN_CONFIRM_DELETE = "✅ Да, удалить"
BTN_CANCEL = "Отмена"

# Управление чатами (Сообщения) (bot.handlers, bot.callbacks, bot.tools)
CHAT_NEW_SUCCESS = "✅ Новый чат создан. Задайте первый вопрос!"
CHAT_CREATE_ERROR = "Ошибка при создании чата."
CHAT_NOT_FOUND = "Активный чат не найден."
CHAT_NO_ACTIVE = "У вас нет активного чата."
CHAT_NO_ANY = "У вас нет активных чатов. Напишите /newchat чтобы создать."
CHAT_SWITCH_ERROR = "Ошибка: чат не найден или вам не принадлежит."
CHAT_DELETE_CANCELLED = "Действие отменено."
CHAT_RENAME_PROMPT = "Введите новое название для чата (не более 60 символов):"
CHAT_RENAME_EMPTY = "Название не может быть пустым. Введите название:"
CHAT_CLEARED = "ℹ️ История чата очищена. Начинайте новый разговор!"
CHAT_HISTORY_EMPTY = "История пуста. Задайте первый вопрос!"

# Функции для динамических строк (bot.handlers, bot.callbacks, bot.tools)
def chat_limit_reached(limit: int) -> str:
    return f"Достигнут лимит в {limit} чатов. Удалите старые, чтобы создать новые."

def chat_limit_reached_auto(limit: int) -> str:
    return f"Достигнут лимит в {limit} чатов. Невозможно автоматически создать новый. Пожалуйста, удалите старые чаты через меню /chats."

def chat_limit_warning(limit: int, count: int) -> str:
    return f"У вас уже {count} чатов. Близок лимит ({limit}). Рекомендуем удалить ненужные."

def chat_switched(title: str) -> str:
    return f"ℹ️ Вы переключились на чат «{title}»."

def chat_delete_confirm(title: str) -> str:
    return f"Удалить чат «{title}»? Это действие нельзя отменить."

def chat_deleted(title: str) -> str:
    return f"ℹ️ Чат «{title}» удалён.\n\nПожалуйста, выберите другой чат:"


def chat_deleted_last(title: str) -> str:
    return f"ℹ️ Чат «{title}» удалён."

def chat_renamed(title: str) -> str:
    return f"✅ Чат переименован в «{title}»."

# Длинные статические тексты (bot.handlers)
CMD_HELP = (
    "ℹ️ Доступные команды:\n\n"
    "/newchat — новый чат\n"
    "/chats — список чатов\n"
    "/rename — переименовать текущий чат\n"
    "/delete — удалить текущий чат\n"
    "/clear — очистить историю сообщений текущего чата\n"
    "/history — последние реплики\n"
    "/stats — статистика"
)

CHATS_LIST = "Ваши чаты:"

def chat_stats(stats: dict) -> str:
    return (
        f"ℹ️ Ваша статистика:\n"
        f"• Всего чатов: {stats['total_chats']}\n"
        f"• Сообщений в текущем чате: {stats['current_chat_messages']}\n"
        f"• Всего сообщений: {stats['total_messages']}\n"
        f"• Всего токенов: {stats['total_tokens']}\n"
        f"• Зарегистрированы: {stats['registered_at']}"
    )

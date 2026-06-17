import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_PATH = "db/bot_users.db"


CREATE_USERS_TABLE = """
create table if not exists users (
    id integer primary key autoincrement,
    max_user_id integer unique not null,
    full_name text not null,
    email text unique not null,
    phone text unique not null,
    registered_at datetime default current_timestamp
);
"""

CREATE_CHAT_MESSAGES_TABLE = """
create table if not exists chat_messages (
    id integer primary key autoincrement,
    max_user_id integer not null,
    role text not null,
    content text not null,
    model text not null,
    prompt_tokens integer,
    completion_tokens integer,
    total_tokens integer generated always as (prompt_tokens + completion_tokens) virtual,
    duration_ms integer,
    created_at datetime default current_timestamp
);
"""

CREATE_IDX_CHAT_MESSAGES_USER = """
create index if not exists idx_chat_messages_max_user_id on chat_messages(max_user_id);
"""

CREATE_IDX_CHAT_MESSAGES_DATE = """
create index if not exists idx_chat_messages_created_at on chat_messages(created_at);
"""

SELECT_USER_BY_ID = "select max_user_id from users where max_user_id=?;"
SELECT_USER_ID_BY_EMAIL = "select id from users where email=?;"
SELECT_USER_ID_BY_PHONE = "select id from users where phone=?;"
INSERT_USER = "insert into users (max_user_id, full_name, email, phone) values (?, ?, ?, ?);"
SELECT_CHAT_HISTORY = "select role, content from chat_messages where max_user_id = ? order by created_at desc limit ?;"
INSERT_CHAT_MESSAGE = """
insert into chat_messages (max_user_id, role, content, model, prompt_tokens, completion_tokens, duration_ms)
values (?, ?, ?, ?, ?, ?, ?);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS_TABLE)
        await db.execute(CREATE_CHAT_MESSAGES_TABLE)
        await db.execute(CREATE_IDX_CHAT_MESSAGES_USER)
        await db.execute(CREATE_IDX_CHAT_MESSAGES_DATE)
        await db.commit()


async def search_user(max_user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_USER_BY_ID, (max_user_id,))
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка БД при поиске пользователя {max_user_id}: {e}")
        return False


async def is_email_registered(email: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_USER_ID_BY_EMAIL, (email,))
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка БД при поиске email {email}: {e}")
        return True


async def is_phone_registered(phone: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_USER_ID_BY_PHONE, (phone,))
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка БД при поиске телефона {phone}: {e}")
        return True


async def add_user(user: dict):
    logger.info(f"Попытка добавить пользователя {user['max_user_id']} в базу данных")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                INSERT_USER,
                (user["max_user_id"], user["full_name"], user["email"], user["phone"]),
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка БД при добавлении пользователя: {e}")
        raise e


async def get_chat_history(max_user_id: str, limit: int) -> list[dict]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_CHAT_HISTORY, (max_user_id, limit))
            rows = await cursor.fetchall()
            return [{'role': r[0], 'content': r[1]} for r in reversed(rows)]
    except Exception as e:
        logger.error(f"Ошибка БД при получении истории для {max_user_id}: {e}")
        return []


async def add_chat_message(max_user_id: int, role: str, content: str, model: str, prompt_tokens: int, completion_tokens: int, duration_ms: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                INSERT_CHAT_MESSAGE,
                (max_user_id, role, content, model, prompt_tokens, completion_tokens, duration_ms),
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка БД при добавлении сообщения для {max_user_id}: {e}")

async def clear_chat_history(max_user_id: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("delete from chat_messages where max_user_id = ?", (max_user_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка БД при очистке истории для {max_user_id}: {e}")

async def get_chat_stats(max_user_id: int) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor_stats = await db.execute("select count(*), coalesce(sum(total_tokens), 0) from chat_messages where max_user_id = ?", (max_user_id,))
            stats_row = await cursor_stats.fetchone()
            
            cursor_reg = await db.execute("select date(registered_at) from users where max_user_id = ?", (max_user_id,))
            reg_row = await cursor_reg.fetchone()
            
            return {
                'total_messages': stats_row[0] if stats_row else 0,
                'total_tokens': stats_row[1] if stats_row else 0,
                'registered_at': reg_row[0] if reg_row else "неизвестно"
            }
    except Exception as e:
        logger.error(f"Ошибка БД при получении статистики для {max_user_id}: {e}")
        return {'total_messages': 0, 'total_tokens': 0, 'registered_at': 'неизвестно'}

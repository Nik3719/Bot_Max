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
    current_chat_id integer,
    registered_at datetime default current_timestamp
);
"""

CREATE_CHATS_TABLE = """
create table if not exists chats (
    id integer primary key autoincrement,
    max_user_id integer not null,
    title text not null default 'Новый чат',
    is_deleted integer default 0,
    created_at datetime default current_timestamp,
    updated_at datetime default current_timestamp
);
"""

CREATE_CHAT_MESSAGES_TABLE = """
create table if not exists chat_messages (
    id integer primary key autoincrement,
    chat_id integer not null,
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

CREATE_IDX_CHAT_MESSAGES_USER = "create index if not exists idx_chat_messages_max_user_id on chat_messages(max_user_id);"
CREATE_IDX_CHAT_MESSAGES_CHAT = "create index if not exists idx_chat_messages_chat_id on chat_messages(chat_id);"
CREATE_IDX_CHAT_MESSAGES_DATE = "create index if not exists idx_chat_messages_created_at on chat_messages(created_at);"

SELECT_USER_BY_ID = "select max_user_id from users where max_user_id=?;"
SELECT_USER_ID_BY_EMAIL = "select id from users where email=?;"
SELECT_USER_ID_BY_PHONE = "select id from users where phone=?;"
INSERT_USER = "insert into users (max_user_id, full_name, email, phone) values (?, ?, ?, ?);"
SELECT_CHAT_HISTORY = "select role, content from chat_messages where chat_id = ? order by created_at desc, id desc limit ?;"
INSERT_CHAT_MESSAGE = """
insert into chat_messages (chat_id, max_user_id, role, content, model, prompt_tokens, completion_tokens, duration_ms)
values (?, ?, ?, ?, ?, ?, ?, ?);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS_TABLE)
        await db.execute(CREATE_CHATS_TABLE)
        await db.execute(CREATE_CHAT_MESSAGES_TABLE)
        await db.execute(CREATE_IDX_CHAT_MESSAGES_USER)
        await db.execute(CREATE_IDX_CHAT_MESSAGES_CHAT)
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

async def get_chat_history(chat_id: int, limit: int) -> list[dict]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(SELECT_CHAT_HISTORY, (chat_id, limit))
            rows = await cursor.fetchall()
            return [{'role': r[0], 'content': r[1]} for r in reversed(rows)]
    except Exception as e:
        logger.error(f"Ошибка БД при получении истории для {chat_id}: {e}")
        return []

async def add_chat_message(chat_id: int, max_user_id: int, role: str, content: str, model: str, prompt_tokens: int, completion_tokens: int, duration_ms: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                INSERT_CHAT_MESSAGE,
                (chat_id, max_user_id, role, content, model, prompt_tokens, completion_tokens, duration_ms),
            )
            await db.execute("update chats set updated_at = current_timestamp where id = ?", (chat_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка БД при добавлении сообщения: {e}")

async def clear_chat_history(chat_id: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("delete from chat_messages where chat_id = ?", (chat_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка БД при очистке истории для {chat_id}: {e}")

async def get_chat_stats(max_user_id: int, current_chat_id: int = None) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor_stats = await db.execute("select count(*), coalesce(sum(total_tokens), 0) from chat_messages where max_user_id = ?", (max_user_id,))
            stats_row = await cursor_stats.fetchone()
            
            chat_msg_count = 0
            if current_chat_id:
                cursor_chat = await db.execute("select count(*) from chat_messages where chat_id = ?", (current_chat_id,))
                chat_row = await cursor_chat.fetchone()
                chat_msg_count = chat_row[0] if chat_row else 0
            
            cursor_chats = await db.execute("select count(*) from chats where max_user_id = ? and is_deleted = 0", (max_user_id,))
            chats_count = await cursor_chats.fetchone()

            cursor_reg = await db.execute("select date(registered_at) from users where max_user_id = ?", (max_user_id,))
            reg_row = await cursor_reg.fetchone()
            
            return {
                'total_messages': stats_row[0] if stats_row else 0,
                'current_chat_messages': chat_msg_count,
                'total_tokens': stats_row[1] if stats_row else 0,
                'total_chats': chats_count[0] if chats_count else 0,
                'registered_at': reg_row[0] if reg_row else "неизвестно"
            }
    except Exception as e:
        logger.error(f"Ошибка БД при получении статистики для {max_user_id}: {e}")
        return {'total_messages': 0, 'current_chat_messages': 0, 'total_tokens': 0, 'total_chats': 0, 'registered_at': 'неизвестно'}

async def create_chat(max_user_id: int, title: str = "Новый чат") -> int:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("insert into chats (max_user_id, title) values (?, ?)", (max_user_id, title))
            chat_id = cursor.lastrowid
            await db.execute("update users set current_chat_id = ? where max_user_id = ?", (chat_id, max_user_id))
            await db.commit()
            return chat_id
    except Exception as e:
        logger.error(f"Ошибка при создании чата для {max_user_id}: {e}")
        return None

async def get_user_chats(max_user_id: int) -> list[dict]:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("select id, title, created_at, updated_at from chats where max_user_id = ? and is_deleted = 0 order by updated_at desc", (max_user_id,))
            rows = await cursor.fetchall()
            return [{'id': r[0], 'title': r[1], 'created_at': r[2], 'updated_at': r[3]} for r in rows]
    except Exception as e:
        logger.error(f"Ошибка при получении чатов пользователя {max_user_id}: {e}")
        return []

async def get_chat(chat_id: int) -> dict:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("select id, max_user_id, title, is_deleted from chats where id = ?", (chat_id,))
            row = await cursor.fetchone()
            if row:
                return {'id': row[0], 'max_user_id': row[1], 'title': row[2], 'is_deleted': row[3]}
            return None
    except Exception as e:
        logger.error(f"Ошибка при получении чата {chat_id}: {e}")
        return None

async def update_chat_title(chat_id: int, title: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("update chats set title = ?, updated_at = current_timestamp where id = ?", (title, chat_id))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при переименовании чата {chat_id}: {e}")

async def delete_chat(chat_id: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("update chats set is_deleted = 1, updated_at = current_timestamp where id = ?", (chat_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при удалении чата {chat_id}: {e}")

async def get_current_chat_id(max_user_id: int) -> int:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("select current_chat_id from users where max_user_id = ?", (max_user_id,))
            row = await cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Ошибка при получении текущего чата для {max_user_id}: {e}")
        return None

async def set_current_chat_id(max_user_id: int, chat_id: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("update users set current_chat_id = ? where max_user_id = ?", (chat_id, max_user_id))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при установке текущего чата {chat_id} для {max_user_id}: {e}")

async def count_user_chats(max_user_id: int) -> int:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("select count(*) from chats where max_user_id = ? and is_deleted = 0", (max_user_id,))
            row = await cursor.fetchone()
            return row[0] if row else 0
    except Exception as e:
        logger.error(f"Ошибка при подсчете чатов для {max_user_id}: {e}")
        return 0

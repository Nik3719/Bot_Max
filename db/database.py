import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_PATH = "db/bot_users.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            create table if not exists users (
                id integer primary key autoincrement,
                max_user_id text unique not null,
                full_name text not null,
                email text unique not null,
                phone text unique not null,
                registered_at datetime default current_timestamp
                )""")
        await db.commit()


async def search_user(max_user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
            select max_user_id from users where max_user_id=?;
            """,
                (max_user_id,),
            )
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка БД при поиске пользователя {max_user_id}: {e}")
        return False


async def is_email_registered(email: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "select id from users where email=?;",
                (email,),
            )
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка БД при поиске email {email}: {e}")
        return True # В случае ошибки лучше не пропускать регистрацию


async def is_phone_registered(phone: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "select id from users where phone=?;",
                (phone,),
            )
            return await cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Ошибка БД при поиске телефона {phone}: {e}")
        return True



async def add_user(user: dict):
    logger.info(f"Попытка добавить пользователя {user['max_user_id']} в базу данных")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
            insert into users (max_user_id,full_name,email,phone) values(?,?,?,?);
            """,
                (user["max_user_id"], user["full_name"], user["email"], user["phone"]),
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка БД при добавлении пользователя: {e}")
        raise e




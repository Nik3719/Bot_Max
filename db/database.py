import aiosqlite

DB_PATH = "db/bot_users.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            create table if not exists users (
                id integer primary key autoincrement,
                max_user_id text unique not null,
                full_name text not null,
                email text not null,
                phone text not null,
                registered_at datetime default current_timestamp
                )""")
        await db.commit()

async def search_user(max_user_id:int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
        select max_user_id from users where max_user_id=?;
        """,(max_user_id,))
        return await cursor.fetchone() is not None

async def add_user(user:dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        insert into users (max_user_id,full_name,email,phone) values(?,?,?,?);
        """,(user["max_user_id"],user["full_name"],user["email"],user["phone"]))
        await db.commit()

async def get_user(max_user_id:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
        select * from users where max_user_id=?
        """,(max_user_id,))
        return await cursor.fetchone()


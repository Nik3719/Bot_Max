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

UPDATE_CHAT_UPDATED_AT = "update chats set updated_at = current_timestamp where id = ?"
DELETE_CHAT_MESSAGES = "delete from chat_messages where chat_id = ?"
SELECT_USER_STATS = "select count(*), coalesce(sum(total_tokens), 0) from chat_messages where max_user_id = ?"
SELECT_CHAT_MESSAGES_COUNT = "select count(*) from chat_messages where chat_id = ?"
SELECT_ACTIVE_CHATS_COUNT = "select count(*) from chats where max_user_id = ? and is_deleted = 0"
SELECT_USER_REGISTRATION_DATE = "select date(registered_at) from users where max_user_id = ?"
INSERT_CHAT = "insert into chats (max_user_id, title) values (?, ?)"
UPDATE_USER_CURRENT_CHAT = "update users set current_chat_id = ? where max_user_id = ?"
SELECT_USER_CHATS = "select id, title, created_at, updated_at from chats where max_user_id = ? and is_deleted = 0 order by updated_at desc"
SELECT_CHAT_BY_ID = "select id, max_user_id, title, is_deleted from chats where id = ?"
UPDATE_CHAT_TITLE = "update chats set title = ?, updated_at = current_timestamp where id = ?"
SOFT_DELETE_CHAT = "update chats set is_deleted = 1, updated_at = current_timestamp where id = ?"
SELECT_USER_CURRENT_CHAT = "select current_chat_id from users where max_user_id = ?"

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("""Токен бота не найден!
    Убедитесь, что переменная BOT_TOKEN задана в файле .env""")

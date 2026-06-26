import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_LINK = os.getenv("BOT_LINK", "")

# Ollama Settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 120))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", 0.7))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", 4096))
OLLAMA_SYSTEM_PROMPT = os.getenv(
    "OLLAMA_SYSTEM_PROMPT", 
    "Ты полезный ассистент. Отвечай на русском языке, если вопрос задан на русском."
)
CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", 10))
MAX_CHATS_PER_USER = int(os.getenv("MAX_CHATS_PER_USER", 50))
CHAT_TITLE_MAX_LEN = int(os.getenv("CHAT_TITLE_MAX_LEN", 60))
AUTO_TITLE_MAX_LEN = int(os.getenv("AUTO_TITLE_MAX_LEN", 30))
CHAT_PREVIEW_LINES = int(os.getenv("CHAT_PREVIEW_LINES", 3))
if not BOT_TOKEN:
    raise ValueError("""Токен бота не найден!
    Убедитесь, что переменная BOT_TOKEN задана в файле .env""")
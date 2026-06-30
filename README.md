Бот MAX

Бот для мессенджера MAX, реализующий пошаговую регистрацию пользователей с валидацией введенных контактных данных (ФИО, email, телефон) и их сохранением в базу данных SQLite.

Установка Ollama и модели для работы ИИ:

1. Скачать и установить Ollama.
   Выполнить в терминале команду:

   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```
2. Скачать модель.
   Открыть терминал и ввести команду:

   ```bash
   ollama run qwen2:0.5b
   ```

   Дождаться окончания загрузки. Убедиться, что Ollama запущена перед работой бота.

Запуск самого бота:

Склонировать репозиторий:

```bash
git clone https://github.com/Nik3719/Bot_Max.git
cd ./Bot_Max
```

Создать и активировать виртуальное окружение:

```bash
python3 -m venv venv
source venv/bin/activate
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

Создать файл `.env` и добавить в него следующие переменные:

```env
BOT_TOKEN=ваш_токен
BOT_LINK=https://max.ru/id_bot
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_TIMEOUT=120
OLLAMA_TEMPERATURE=0.7
OLLAMA_NUM_CTX=4096
OLLAMA_SYSTEM_PROMPT="Ты полезный ассистент. Отвечай на русском языке, если вопрос задан на русском."
CHAT_HISTORY_LIMIT=10
MAX_CHATS_PER_USER=50
CHAT_TITLE_MAX_LEN=60
AUTO_TITLE_MAX_LEN=30
CHAT_PREVIEW_LINES=3
```

Запустить проект:

```bash
python main.py
```



Для быстрого развертывания проекта (бота и Ollama) можно использовать Docker.

1. В репозитории есть шаблон файла переменных окружения. Скопируйте его и переименуйте в `.env`:

   ```bash
   cp .env.example .env
   ```

   В файл `.env` впишите реальные данные (`BOT_TOKEN`).
2. Запустите проект через Docker Compose :

   ```bash
   docker compose up -d
   ```
3. Скачайте нужную модель внутри запущенного контейнера Ollama.

```
   docker exec -it max_ollama ollama pull qwen2:0.5b
```

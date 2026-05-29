import os
from dotenv import load_dotenv

# Загрузка локальных переменных из файла .env (для тестов на ПК)
load_dotenv()

# Извлечение секретного токена из окружения хостинга или .env
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ Критическая ошибка: Переменная окружения BOT_TOKEN не задана!")

# Имя файла базы данных SQLite
DB_NAME = "vpi_game.db"
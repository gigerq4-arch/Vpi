import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import router, ActivityMiddleware

async def main():
    # Настройка логов для удаленного мониторинга работы через консоль
    logging.basicConfig(level=logging.INFO)
    
    # Инициализация структуры таблиц базы данных SQLite
    await init_db()
    
    # Запуск ядра бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрация глобального класса-middleware для отслеживания юзернеймов
    router.message.middleware(ActivityMiddleware())
    
    # Подключение главного игрового роутера со всеми хендлерами
    dp.include_router(router)
    
    print("🚀 Старт систем ВПИ-Бота. Служба безопасности инициализирована успешно.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from bot_handlers import register_handlers, send_message_to_user
from database import init_db, save_message
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Регистрация обработчиков"""
        register_handlers(self.application)
    
    async def send_admin_message(self, user_id: int, message: str):
        """Публичный метод для отправки сообщений от администратора"""
        return await send_message_to_user(self.application.bot, user_id, message)
    
    def run(self):
        """Запуск бота"""
        print("🤖 Бот запущен...")
        print("📊 Используйте /start для начала работы")
        self.application.run_polling()

def main():
    # Инициализация базы данных
    init_db()
    
    # Токен бота
    BOT_TOKEN = os.environ['TELEGRAM_BOT']
    
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Ошибка: Установите TELEGRAM_BOT_TOKEN в переменных окружения")
        print("💡 Получите токен у @BotFather в Telegram")
        return
    
    # Запуск бота
    bot = TelegramBot(BOT_TOKEN)
    bot.run()

if __name__ == '__main__':
    main()

import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from bot_handlers import register_handlers
from database import init_db

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
    
    def run(self):
        """Запуск бота"""
        print("🤖 Бот запущен...")
        print("📊 Используйте /start для начала работы")
        self.application.run_polling()

def main():
    # Инициализация базы данных
    init_db()
    
    # Токен бота
    BOT_TOKEN = "8256261302:AAEGdLaIdoiwFGc0Zagr6A1kvqtErscj7Wo"
    
    # Запуск бота
    bot = TelegramBot(BOT_TOKEN)
    bot.run()

if __name__ == '__main__':
    main()

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler
from database import save_user, save_message, create_support_ticket

# Состояния для ConversationHandler
MANAGER_DIALOG, REPORT_ISSUE, WAITING_MEDIA = range(3)

def create_main_menu():
    """Создание главного меню"""
    keyboard = [
        [KeyboardButton("👨‍💼 Обратиться к менеджеру")],
        [KeyboardButton("⚠️ Отчет о нарушении")],
        [KeyboardButton("🏢 Информация об организации")],
        [KeyboardButton("📅 График работы"), KeyboardButton("💰 Расчет ЗП")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    save_user(user.id, user.first_name, user.username)
    
    welcome_text = f"""
Приветствую, {user.first_name}! 
Я бот технической поддержки. Выберите нужный вариант:
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=create_main_menu()
    )

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка главного меню"""
    text = update.message.text
    user_id = update.effective_user.id
    save_message(user_id, text, 'user')
    
    if text == "👨‍💼 Обратиться к менеджеру":
        await update.message.reply_text(
            "Опишите вашу проблему или вопрос. Менеджер свяжется с вами в ближайшее время.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True)
        )
        return MANAGER_DIALOG
    
    elif text == "⚠️ Отчет о нарушении":
        await update.message.reply_text(
            "Опишите нарушение и при необходимости прикрепите фото/видео:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True)
        )
        return REPORT_ISSUE
    
    elif text == "🏢 Информация об организации":
        org_info = """
🏢 Наша организация:
• Основана в 2010 году
• Специализация: IT решения
• Штат: 50+ сотрудников
• Контакты: +7 (XXX) XXX-XX-XX
        """
        await update.message.reply_text(org_info)
    
    elif text == "📅 График работы":
        schedule = """
🕒 График работы сотрудников:
Пн-Пт: 9:00 - 18:00
Сб: 10:00 - 15:00
Вс: выходной
Обед: 13:00 - 14:00
        """
        await update.message.reply_text(schedule)
    
    elif text == "💰 Расчет ЗП":
        salary_info = """
💰 Расчет заработной платы:
• Оклад: согласно должности
• Премии: за выполнение KPI
• Надбавки: за стаж и проекты
• Аванс: 40% 15-го числа
• Основная выплата: 5-го числа
        """
        await update.message.reply_text(salary_info)
    
    return ConversationHandler.END

async def handle_manager_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка диалога с менеджером"""
    if update.message.text == "❌ Отмена":
        await update.message.reply_text("Диалог отменен", reply_markup=create_main_menu())
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Сохраняем обращение в базу
    ticket_id = create_support_ticket(user_id, message_text, 'manager_request')
    
    await update.message.reply_text(
        f"✅ Ваше обращение #{ticket_id} принято! Менеджер свяжется с вами в течение 15 минут.",
        reply_markup=create_main_menu()
    )
    
    return ConversationHandler.END

async def handle_report_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка отчета о нарушении"""
    if update.message.text == "❌ Отмена":
        await update.message.reply_text("Создание отчета отменено", reply_markup=create_main_menu())
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    
    if update.message.photo or update.message.document or update.message.video:
        # Обработка медиа-файлов
        media_info = "Медиафайл получен"
        if update.message.caption:
            media_info += f" с описанием: {update.message.caption}"
        
        ticket_id = create_support_ticket(user_id, media_info, 'violation_report')
        
        await update.message.reply_text(
            f"✅ Отчет о нарушении #{ticket_id} создан! Спасибо за бдительность.",
            reply_markup=create_main_menu()
        )
        return ConversationHandler.END
    
    elif update.message.text:
        ticket_id = create_support_ticket(user_id, update.message.text, 'violation_report')
        
        await update.message.reply_text(
            f"✅ Отчет о нарушении #{ticket_id} создан! Хотите прикрепить фото/видео?",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("✅ Да, прикрепить"), KeyboardButton("❌ Нет, завершить")]
            ], resize_keyboard=True)
        )
        return WAITING_MEDIA
    
    return REPORT_ISSUE

async def handle_media_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка прикрепления медиа"""
    if update.message.text == "❌ Нет, завершить":
        await update.message.reply_text("Отчет завершен", reply_markup=create_main_menu())
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Прикрепите фото или видео нарушения:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Завершить без медиа")]], resize_keyboard=True)
    )
    return REPORT_ISSUE

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отмены"""
    await update.message.reply_text("Действие отменено", reply_markup=create_main_menu())
    return ConversationHandler.END

def register_handlers(application):
    """Регистрация всех обработчиков"""
    
    # ConversationHandler для сложных сценариев
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
        states={
            MANAGER_DIALOG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manager_dialog)
            ],
            REPORT_ISSUE: [
                MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_report_issue)
            ],
            WAITING_MEDIA: [
                MessageHandler(filters.TEXT, handle_media_attachment)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_handler)]
    )
    
    # Базовые обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(conv_handler)
    
    # Обработчик для любых других сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler
from database import save_user, save_message, create_support_ticket, save_media_file
import os

# Настройка логирования
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
MAIN_MENU, MANAGER_DIALOG, REPORT_ISSUE, WAITING_MEDIA = range(4)

def create_main_menu():
    """Создание главного меню"""
    keyboard = [
        [KeyboardButton("👨‍💼 Обратиться к менеджеру")],
        [KeyboardButton("⚠️ Отчет о нарушении")],
        [KeyboardButton("🏢 Информация об организации")],
        [KeyboardButton("📅 График работы"), KeyboardButton("💰 Расчет ЗП")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_back_menu():
    """Меню с кнопкой назад"""
    return ReplyKeyboardMarkup([[KeyboardButton("↩️ Назад в меню")]], resize_keyboard=True)

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
    return MAIN_MENU

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка главного меню"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "👨‍💼 Обратиться к менеджеру":
        save_message(user_id, "Обратиться к менеджеру", 'user')
        await update.message.reply_text(
            "Опишите вашу проблему или вопрос. Менеджер свяжется с вами в ближайшее время.",
            reply_markup=create_back_menu()
        )
        return MANAGER_DIALOG
    
    elif text == "⚠️ Отчет о нарушении":
        save_message(user_id, "Отчет о нарушении", 'user')
        await update.message.reply_text(
            "Опишите нарушение и при необходимости прикрепите фото/видео:",
            reply_markup=create_back_menu()
        )
        # Создаем тикет для отчетов
        ticket_id = create_support_ticket(user_id, "Отчет о нарушении (начало)", 'violation_report')
        context.user_data['current_ticket_id'] = ticket_id
        return REPORT_ISSUE
    
    elif text == "🏢 Информация об организации":
        save_message(user_id, "Информация об организации", 'user')
        org_info = """
🏢 Наша организация:
• Основана в 2010 году
• Специализация: IT решения
• Штат: 50+ сотрудников
• Контакты: +7 (XXX) XXX-XX-XX

Мы стремимся к созданию комфортных условий для наших сотрудников и развитию технологий.
        """
        await update.message.reply_text(org_info, reply_markup=create_main_menu())
        return MAIN_MENU
    
    elif text == "📅 График работы":
        save_message(user_id, "График работы", 'user')
        schedule = """
🕒 График работы сотрудников:
Пн-Пт: 9:00 - 18:00
Сб: 10:00 - 15:00
Вс: выходной
Обед: 13:00 - 14:00

⚡ Экстренная поддержка: круглосуточно
        """
        await update.message.reply_text(schedule, reply_markup=create_main_menu())
        return MAIN_MENU
    
    elif text == "💰 Расчет ЗП":
        save_message(user_id, "Расчет ЗП", 'user')
        salary_info = """
💰 Расчет заработной платы:

• Оклад: согласно должности
• Премии: за выполнение KPI
• Надбавки: за стаж и проекты
• Аванс: 40% 15-го числа
• Основная выплата: 5-го числа

📊 Для точного расчета обратитесь к менеджеру.
        """
        await update.message.reply_text(salary_info, reply_markup=create_main_menu())
        return MAIN_MENU
    
    elif text == "↩️ Назад в меню":
        save_message(user_id, "Назад в меню", 'user')
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=create_main_menu()
        )
        # Очищаем временные данные
        context.user_data.pop('current_ticket_id', None)
        return MAIN_MENU
    
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите один из вариантов меню:",
            reply_markup=create_main_menu()
        )
        return MAIN_MENU

async def handle_manager_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка диалога с менеджером"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "↩️ Назад в меню":
        save_message(user_id, "Отмена обращения к менеджеру", 'user')
        await update.message.reply_text(
            "Обращение к менеджеру отменено.",
            reply_markup=create_main_menu()
        )
        return MAIN_MENU
    
    # Сохраняем сообщение пользователя
    save_message(user_id, text, 'user')
    
    # Создаем тикет для обращения к менеджеру
    ticket_id = create_support_ticket(user_id, text, 'manager_request')
    
    await update.message.reply_text(
        f"✅ Ваше обращение #{ticket_id} принято! Менеджер свяжется с вами в течение 15 минут.",
        reply_markup=create_main_menu()
    )
    
    return MAIN_MENU

async def handle_media_file(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket_id: int):
    """Обработка медиафайлов"""
    user_id = update.effective_user.id
    
    try:
        # Определяем тип файла и получаем файл
        if update.message.photo:
            file = await update.message.photo[-1].get_file()
            file_type = 'photo'
            caption = update.message.caption
        elif update.message.video:
            file = await update.message.video.get_file()
            file_type = 'video'
            caption = update.message.caption
        elif update.message.document:
            file = await update.message.document.get_file()
            file_type = 'document'
            caption = update.message.caption
        else:
            await update.message.reply_text(
                "❌ Неподдерживаемый тип файла.",
                reply_markup=create_back_menu()
            )
            return
        
        # Сохраняем файл локально
        file_extension = '.jpg' if file_type == 'photo' else os.path.splitext(file.file_path)[1] if file.file_path else '.bin'
        filename = f"{user_id}_{ticket_id}_{file.file_id}{file_extension}"
        file_path = os.path.join('media', filename)
        
        # Создаем папку media если её нет
        os.makedirs('media', exist_ok=True)
        
        # Скачиваем файл
        await file.download_to_drive(file_path)
        
        # Сохраняем информацию о файле в базу
        save_media_file(user_id, ticket_id, file.file_id, file_type, filename, caption)
        
        # Сохраняем сообщение о файле
        media_message = f"Прикрепил {file_type}: {filename}"
        if caption:
            media_message += f" с подписью: {caption}"
        save_message(user_id, media_message, 'user')
        
        await update.message.reply_text(
            "✅ Файл успешно прикреплен к отчету! Можете прикрепить еще файлы или завершить отчет.",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("✅ Прикрепить еще файл")],
                [KeyboardButton("❌ Завершить отчет")]
            ], resize_keyboard=True)
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки медиафайла: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке файла. Попробуйте еще раз.",
            reply_markup=create_back_menu()
        )

async def handle_report_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка отчета о нарушении"""
    user_id = update.effective_user.id
    current_ticket_id = context.user_data.get('current_ticket_id')
    
    if not current_ticket_id:
        # Создаем новый тикет если его нет
        current_ticket_id = create_support_ticket(user_id, "Отчет о нарушении", 'violation_report')
        context.user_data['current_ticket_id'] = current_ticket_id
    
    if update.message.text == "↩️ Назад в меню":
        save_message(user_id, "Отмена отчета о нарушении", 'user')
        await update.message.reply_text(
            "Создание отчета отменено.",
            reply_markup=create_main_menu()
        )
        context.user_data.pop('current_ticket_id', None)
        return MAIN_MENU
    
    # Обработка текстовых сообщений
    if update.message.text and update.message.text not in ["✅ Прикрепить еще файл", "❌ Завершить отчет"]:
        save_message(user_id, update.message.text, 'user')
        
        # Обновляем описание тикета
        from database import update_ticket_status
        update_ticket_status(current_ticket_id, 'open', f"Описание нарушения: {update.message.text}")
        
        await update.message.reply_text(
            "✅ Описание нарушения сохранено! Хотите прикрепить фото/видео?",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("✅ Да, прикрепить файл")],
                [KeyboardButton("❌ Нет, завершить отчет")]
            ], resize_keyboard=True)
        )
        return WAITING_MEDIA
    
    # Обработка медиафайлов
    elif update.message.photo or update.message.video or update.message.document:
        await handle_media_file(update, context, current_ticket_id)
        return REPORT_ISSUE
    
    return REPORT_ISSUE

async def handle_media_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка решения о прикреплении медиа"""
    user_id = update.effective_user.id
    text = update.message.text
    current_ticket_id = context.user_data.get('current_ticket_id')
    
    if text == "✅ Да, прикрепить файл":
        save_message(user_id, "Решил прикрепить файл", 'user')
        await update.message.reply_text(
            "Прикрепите фото, видео или документ:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Завершить без файла")]], resize_keyboard=True)
        )
        return REPORT_ISSUE
    
    elif text == "❌ Нет, завершить отчет" or text == "❌ Завершить без файла":
        save_message(user_id, "Завершил отчет без файла", 'user')
        await update.message.reply_text(
            f"✅ Отчет о нарушении #{current_ticket_id} завершен! Спасибо за бдительность.",
            reply_markup=create_main_menu()
        )
        context.user_data.pop('current_ticket_id', None)
        return MAIN_MENU
    
    elif text == "✅ Прикрепить еще файл":
        save_message(user_id, "Хочет прикрепить еще файл", 'user')
        await update.message.reply_text(
            "Прикрепите следующий файл:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Завершить отчет")]], resize_keyboard=True)
        )
        return REPORT_ISSUE
    
    elif text == "❌ Завершить отчет":
        save_message(user_id, "Завершил отчет с файлами", 'user')
        await update.message.reply_text(
            f"✅ Отчет о нарушении #{current_ticket_id} завершен! Спасибо за предоставленную информацию.",
            reply_markup=create_main_menu()
        )
        context.user_data.pop('current_ticket_id', None)
        return MAIN_MENU
    
    return WAITING_MEDIA

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отмены"""
    user_id = update.effective_user.id
    save_message(user_id, "Отмена действия", 'user')
    
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=create_main_menu()
    )
    
    # Очищаем временные данные
    context.user_data.pop('current_ticket_id', None)
    
    return MAIN_MENU

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке сообщения: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.",
            reply_markup=create_main_menu()
        )
    
    return MAIN_MENU

def register_handlers(application):
    """Регистрация всех обработчиков"""
    
    # ConversationHandler для основного потока
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
            ],
            MANAGER_DIALOG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manager_dialog)
            ],
            REPORT_ISSUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report_issue),
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_report_issue)
            ],
            WAITING_MEDIA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_media_decision),
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_report_issue)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_handler)],
        allow_reentry=True
    )
    
    # Базовые обработчики
    application.add_handler(conv_handler)
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("Все обработчики зарегистрированы")

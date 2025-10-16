import requests
import os
from database import save_message

def send_telegram_message(user_id, message):
    """Отправка сообщения пользователю через Telegram Bot API"""
    TELEGRAM_BOT_TOKEN = "8256261302:AAEGdLaIdoiwFGc0Zagr6A1kvqtErscj7Wo"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': user_id,
        'text': f"👨‍💼 Ответ от поддержки:\n\n{message}",
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            # Сохраняем сообщение в базу
            save_message(user_id, message, 'text', True)
            return True, "Сообщение отправлено"
        else:
            return False, f"Ошибка Telegram API: {response.text}"
    except Exception as e:
        return False, f"Ошибка отправки: {str(e)}"

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import pysqlite3 as sqlite3
import os
import hashlib
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# Импортируем функции из database.py
def get_connection():
    return sqlite3.connect('bot_database.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица сообщений
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message_text TEXT,
            message_type TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_from_admin BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Таблица тикетов поддержки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            description TEXT,
            ticket_type TEXT,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            admin_notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Таблица для медиафайлов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ticket_id INTEGER,
            file_id TEXT,
            file_type TEXT,
            file_path TEXT,
            caption TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (ticket_id) REFERENCES support_tickets (id)
        )
    ''')
    
    # Создаем папку для медиафайлов
    os.makedirs('media', exist_ok=True)
    
    conn.commit()
    conn.close()

def save_user(user_id: int, first_name: str, username: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_activity)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, username, first_name))
    conn.commit()
    conn.close()

def save_message(user_id: int, message_text: str, message_type: str = 'text', is_from_admin: bool = False):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (user_id, message_text, message_type, is_from_admin)
        VALUES (?, ?, ?, ?)
    ''', (user_id, message_text, message_type, is_from_admin))
    conn.commit()
    conn.close()

def get_user_by_id(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'registration_date': row[3],
            'last_activity': row[4]
        }
    return None

def get_ticket_by_id(ticket_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT st.*, u.username, u.first_name 
        FROM support_tickets st 
        JOIN users u ON st.user_id = u.user_id 
        WHERE st.id = ?
    ''', (ticket_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'user_id': row[1],
            'description': row[2],
            'ticket_type': row[3],
            'status': row[4],
            'created_at': row[5],
            'resolved_at': row[6],
            'admin_notes': row[7],
            'username': row[8],
            'first_name': row[9]
        }
    return None

def get_media_files_by_ticket(ticket_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM media_files 
        WHERE ticket_id = ? 
        ORDER BY uploaded_at
    ''', (ticket_id,))
    
    media_files = []
    for row in cursor.fetchall():
        media_files.append({
            'id': row[0],
            'user_id': row[1],
            'ticket_id': row[2],
            'file_id': row[3],
            'file_type': row[4],
            'file_path': row[5],
            'caption': row[6],
            'uploaded_at': row[7]
        })
    
    conn.close()
    return media_files

def get_conversation_messages(user_id: int, limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM messages 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (user_id, limit))
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            'id': row[0],
            'user_id': row[1],
            'message_text': row[2],
            'message_type': row[3],
            'timestamp': row[4],
            'is_from_admin': bool(row[5])
        })
    
    conn.close()
    return messages[::-1]

def get_all_tickets(status: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute('''
            SELECT st.*, u.username, u.first_name 
            FROM support_tickets st 
            JOIN users u ON st.user_id = u.user_id 
            WHERE st.status = ?
            ORDER BY st.created_at DESC
        ''', (status,))
    else:
        cursor.execute('''
            SELECT st.*, u.username, u.first_name 
            FROM support_tickets st 
            JOIN users u ON st.user_id = u.user_id 
            ORDER BY st.created_at DESC
        ''')
    
    tickets = []
    for row in cursor.fetchall():
        tickets.append({
            'id': row[0],
            'user_id': row[1],
            'description': row[2],
            'ticket_type': row[3],
            'status': row[4],
            'created_at': row[5],
            'resolved_at': row[6],
            'admin_notes': row[7],
            'username': row[8],
            'first_name': row[9]
        })
    
    conn.close()
    return tickets

def update_ticket_status(ticket_id: int, status: str, admin_notes: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if status == 'resolved':
        cursor.execute('''
            UPDATE support_tickets 
            SET status = ?, admin_notes = ?, resolved_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (status, admin_notes, ticket_id))
    else:
        cursor.execute('''
            UPDATE support_tickets 
            SET status = ?, admin_notes = ? 
            WHERE id = ?
        ''', (status, admin_notes, ticket_id))
    
    conn.commit()
    conn.close()

def get_system_stats():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM support_tickets WHERE status = "open"')
    open_tickets = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM support_tickets WHERE status = "resolved"')
    resolved_tickets = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM messages')
    total_messages = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM media_files')
    total_media = cursor.fetchone()[0]
    
    # Активные пользователи за последние 24 часа
    cursor.execute('SELECT COUNT(*) FROM users WHERE last_activity > datetime("now", "-1 day")')
    active_users = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_users': total_users,
        'open_tickets': open_tickets,
        'resolved_tickets': resolved_tickets,
        'total_messages': total_messages,
        'total_media': total_media,
        'active_users': active_users
    }

# НОВЫЕ ФУНКЦИИ ДЛЯ ПРОСМОТРА БАЗЫ ДАННЫХ
def get_database_info():
    """Получить полную информацию о структуре базы данных"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Получаем список всех таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    db_info = {}
    
    for table in tables:
        # Получаем информацию о столбцах
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        # Получаем количество записей
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        
        # Получаем примеры данных (первые 10 записей)
        cursor.execute(f"SELECT * FROM {table} LIMIT 10")
        data = cursor.fetchall()
        
        # Получаем статистику для таблицы тикетов
        stats = {}
        if table == 'support_tickets':
            cursor.execute("SELECT status, COUNT(*) FROM support_tickets GROUP BY status")
            status_stats = cursor.fetchall()
            stats = {status: count for status, count in status_stats}
            
            cursor.execute("SELECT ticket_type, COUNT(*) FROM support_tickets GROUP BY ticket_type")
            type_stats = cursor.fetchall()
            stats['by_type'] = {ticket_type: count for ticket_type, count in type_stats}
            
            # Среднее время ответа
            cursor.execute('''
                SELECT AVG((julianday(resolved_at) - julianday(created_at)) * 24) 
                FROM support_tickets 
                WHERE resolved_at IS NOT NULL
            ''')
            avg_time = cursor.fetchone()[0]
            stats['avg_response_time'] = round(avg_time or 0, 2)
        
        db_info[table] = {
            'columns': columns,
            'count': count,
            'data': data,
            'stats': stats
        }
    
    conn.close()
    return db_info

def get_database_stats():
    """Получить общую статистику по базе данных"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Количество таблиц
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    total_tables = cursor.fetchone()[0]
    
    # Общее количество записей во всех таблицах
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    total_records = 0
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        total_records += cursor.fetchone()[0]
    
    # Дополнительная статистика
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM support_tickets")
    total_tickets = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM media_files")
    total_media = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_tables': total_tables,
        'total_records': total_records,
        'total_users': total_users,
        'total_tickets': total_tickets,
        'total_messages': total_messages,
        'total_media': total_media
    }

def execute_custom_query(query):
    """Выполнить произвольный SQL-запрос"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(query)
        
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            formatted_results = []
            for row in results:
                formatted_row = {}
                for i, column in enumerate(columns):
                    formatted_row[column] = row[i]
                formatted_results.append(formatted_row)
            
            conn.close()
            return True, formatted_results
        else:
            conn.commit()
            conn.close()
            return True, f"Query executed successfully. Rows affected: {cursor.rowcount}"
            
    except Exception as e:
        conn.close()
        return False, str(e)

# Инициализация Flask приложения
app = Flask(__name__)
app.secret_key = 'admin-secret-key-12345-change-in-production'

# Настройки
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT')

if (TELEGRAM_BOT_TOKEN == ""):
    print("Ключ для телеграмм бота не был установлен")
    
UPLOAD_FOLDER = 'media'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Хэширование паролей
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Администраторы
ADMIN_CREDENTIALS = {
    'admin': hash_password('admin123')
}

def send_telegram_message(user_id, message):
    """Отправка сообщения пользователю через Telegram Bot API"""
    if TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        return False, "Токен бота не настроен"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': user_id,
        'text': f"👨‍💼 Ответ от поддержки:\n\n{message}",
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"[DEBUG] Отправка сообщения пользователю {user_id}: {message}")
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response text: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                # Сохраняем сообщение в базу
                save_message(user_id, message, 'text', True)
                return True, "Сообщение отправлено"
            else:
                error_msg = f"Telegram API error: {data.get('description')}"
                print(f"[DEBUG] {error_msg}")
                return False, error_msg
        else:
            error_msg = f"HTTP error: {response.status_code}"
            print(f"[DEBUG] {error_msg}")
            return False, error_msg
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        print(f"[DEBUG] {error_msg}")
        return False, error_msg

# Маршруты Flask
@app.route('/')
def index():
    if 'admin' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = hash_password(password)
        
        if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == hashed_password:
            session['admin'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Неверные учетные данные')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    stats = get_system_stats()
    open_tickets = get_all_tickets('open')
    
    return render_template('dashboard.html', 
                         stats=stats,
                         open_tickets=open_tickets,
                         admin=session.get('admin'))

@app.route('/tickets')
def tickets_page():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    status = request.args.get('status', 'all')
    if status == 'all':
        tickets = get_all_tickets()
    else:
        tickets = get_all_tickets(status)
    
    return render_template('tickets.html', 
                         tickets=tickets, 
                         status=status,
                         admin=session.get('admin'))

@app.route('/ticket/<int:ticket_id>')
def ticket_detail(ticket_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        return "Тикет не найден", 404
    
    media_files = get_media_files_by_ticket(ticket_id)
    conversation = get_conversation_messages(ticket['user_id'])
    
    return render_template('ticket_detail.html', 
                         ticket=ticket, 
                         media_files=media_files,
                         conversation=conversation,
                         admin=session.get('admin'))

@app.route('/users')
def users_page():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.*, 
               COUNT(DISTINCT m.id) as message_count,
               COUNT(DISTINCT st.id) as ticket_count,
               MAX(m.timestamp) as last_message
        FROM users u
        LEFT JOIN messages m ON u.user_id = m.user_id
        LEFT JOIN support_tickets st ON u.user_id = st.user_id
        GROUP BY u.user_id
        ORDER BY u.last_activity DESC
    ''')
    
    users = []
    for row in cursor.fetchall():
        users.append({
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'registration_date': row[3],
            'last_activity': row[4],
            'message_count': row[5],
            'ticket_count': row[6],
            'last_message': row[7]
        })
    
    conn.close()
    
    return render_template('users.html', users=users, admin=session.get('admin'))

# НОВЫЙ МАРШРУТ ДЛЯ ПРОСМОТРА БАЗЫ ДАННЫХ
@app.route('/database')
def database_page():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    db_info = get_database_info()
    db_stats = get_database_stats()
    
    return render_template('database.html', 
                         db_info=db_info,
                         db_stats=db_stats,
                         admin=session.get('admin'))

@app.route('/media/<path:filename>')
def serve_media(filename):
    if 'admin' not in session:
        return "Unauthorized", 401
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# API endpoints
@app.route('/api/tickets')
def api_tickets():
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    status = request.args.get('status')
    tickets = get_all_tickets(status)
    return jsonify(tickets)

@app.route('/api/tickets/<int:ticket_id>', methods=['PUT'])
def api_update_ticket(ticket_id):
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    status = data.get('status')
    notes = data.get('admin_notes')
    
    update_ticket_status(ticket_id, status, notes)
    return jsonify({'success': True})

@app.route('/api/ticket/<int:ticket_id>/send_message', methods=['POST'])
def api_send_message(ticket_id):
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    data = request.get_json()
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    success, result_message = send_telegram_message(ticket['user_id'], message)
    
    if success:
        return jsonify({'success': True, 'message': result_message})
    else:
        return jsonify({'success': False, 'error': result_message}), 500

@app.route('/api/ticket/<int:ticket_id>/conversation')
def api_get_conversation(ticket_id):
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    conversation = get_conversation_messages(ticket['user_id'])
    return jsonify(conversation)

@app.route('/api/stats')
def api_stats():
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    stats = get_system_stats()
    return jsonify(stats)

@app.route('/api/users')
def api_users():
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY last_activity DESC')
    
    users = []
    for row in cursor.fetchall():
        users.append({
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'registration_date': row[3],
            'last_activity': row[4]
        })
    
    conn.close()
    return jsonify(users)

# НОВЫЕ API ЭНДПОИНТЫ ДЛЯ БАЗЫ ДАННЫХ
@app.route('/api/database/query', methods=['POST'])
def api_execute_query():
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    success, result = execute_custom_query(query)
    
    if success:
        return jsonify({'success': True, 'results': result})
    else:
        return jsonify({'success': False, 'error': result}), 400

@app.route('/api/database/info')
def api_database_info():
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db_info = get_database_info()
    return jsonify(db_info)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

# Создание базовых шаблонов если их нет
def create_basic_templates():
    templates_dir = 'templates'
    os.makedirs(templates_dir, exist_ok=True)
    
    # login.html
    with open(os.path.join(templates_dir, 'login.html'), 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <meta charset="utf-8">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 400px; 
            margin: 100px auto; 
            padding: 20px; 
            background: #f5f5f5;
        }
        .login-form { 
            background: white; 
            padding: 30px; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h2 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        input[type="text"], input[type="password"] { 
            width: 100%; 
            padding: 12px; 
            margin: 10px 0; 
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button { 
            background: #007cba; 
            color: white; 
            padding: 12px 20px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
            width: 100%;
            font-size: 16px;
        }
        button:hover {
            background: #005a87;
        }
        .error { 
            color: red; 
            margin: 10px 0; 
            text-align: center;
            padding: 10px;
            background: #ffe6e6;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="login-form">
        <h2>🔐 Административная панель</h2>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Логин" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
        </form>
        <div style="margin-top: 20px; text-align: center; color: #666; font-size: 12px;">
            По умолчанию: admin / admin123
        </div>
    </div>
</body>
</html>''')

    # dashboard.html
    with open(os.path.join(templates_dir, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
    <meta charset="utf-8">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 0;
            background: #f0f2f5; 
        }
        .header { 
            background: white; 
            padding: 20px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .stats { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin-bottom: 20px;
            padding: 0 20px;
        }
        .stat-card { 
            background: white; 
            padding: 25px; 
            border-radius: 8px; 
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-number { 
            font-size: 2.5em; 
            font-weight: bold; 
            margin: 10px 0; 
            color: #007cba;
        }
        .stat-card h3 {
            margin: 0;
            color: #666;
        }
        .nav { 
            margin: 20px 0; 
        }
        .nav a { 
            margin-right: 20px; 
            text-decoration: none; 
            color: #007cba;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
        }
        .nav a:hover {
            background: #f0f8ff;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        .ticket-list {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .ticket-item {
            padding: 15px;
            border-bottom: 1px solid #eee;
        }
        .ticket-item:last-child {
            border-bottom: none;
        }
        .user-info {
            float: right;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🤖 Панель управления Telegram ботом</h1>
            <div class="user-info">
                👤 {{ admin }} | <a href="/logout" style="color: #ff4444;">Выйти</a>
            </div>
            <div class="nav">
                <a href="/dashboard">📊 Дашборд</a>
                <a href="/tickets">🎫 Все тикеты</a>
                <a href="/tickets?status=open">⚠️ Открытые</a>
                <a href="/tickets?status=resolved">✅ Решенные</a>
                <a href="/users">👥 Пользователи</a>
                <a href="/database">🗃️ База данных</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <h3>👥 Пользователи</h3>
                <div class="stat-number">{{ stats.total_users }}</div>
                <small>Активных: {{ stats.active_users }}</small>
            </div>
            <div class="stat-card">
                <h3>⚠️ Открытые тикеты</h3>
                <div class="stat-number">{{ stats.open_tickets }}</div>
            </div>
            <div class="stat-card">
                <h3>✅ Решенные тикеты</h3>
                <div class="stat-number">{{ stats.resolved_tickets }}</div>
            </div>
            <div class="stat-card">
                <h3>💬 Сообщения</h3>
                <div class="stat-number">{{ stats.total_messages }}</div>
            </div>
            <div class="stat-card">
                <h3>📸 Медиафайлы</h3>
                <div class="stat-number">{{ stats.total_media }}</div>
            </div>
        </div>
        
        <div class="ticket-list">
            <h3>📋 Последние открытые тикеты</h3>
            {% if open_tickets %}
                {% for ticket in open_tickets[:5] %}
                <div class="ticket-item">
                    <strong><a href="/ticket/{{ ticket.id }}">#{{ ticket.id }} - {{ ticket.first_name }}</a></strong>
                    <br>
                    <small>Тип: {{ ticket.ticket_type }} | Создан: {{ ticket.created_at }}</small>
                    <p>{{ ticket.description[:100] }}{% if ticket.description|length > 100 %}...{% endif %}</p>
                </div>
                {% endfor %}
                {% if open_tickets|length > 5 %}
                <div style="text-align: center; margin-top: 15px;">
                    <a href="/tickets?status=open">Показать все {{ open_tickets|length }} открытых тикетов</a>
                </div>
                {% endif %}
            {% else %}
                <p>🎉 Нет открытых тикетов</p>
            {% endif %}
        </div>
    </div>
</body>
</html>''')

    # tickets.html (уже создан ранее)
    # ticket_detail.html (уже создан ранее)
    # users.html (уже создан ранее)

    # database.html - НОВЫЙ ШАБЛОН ДЛЯ ПРОСМОТРА БАЗЫ ДАННЫХ
    with open(os.path.join(templates_dir, 'database.html'), 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="ru">
<head>
    <title>Информация о базе данных</title>
    <meta charset="utf-8">
    <style>
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f6f8fa;
            --bg-tertiary: #fafbfc;
            --border-primary: #e1e4e8;
            --border-secondary: #d1d5da;
            --text-primary: #24292e;
            --text-secondary: #586069;
            --text-tertiary: #6a737d;
            --accent-color: #0366d6;
            --accent-hover: #0256c7;
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
            --shadow-hover: 0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23);
        }

        .dark-theme {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border-primary: #30363d;
            --border-secondary: #3b424a;
            --text-primary: #f0f6fc;
            --text-secondary: #c9d1d9;
            --text-tertiary: #8b949e;
            --accent-color: #58a6ff;
            --accent-hover: #4493f1;
            --success-color: #3fb950;
            --warning-color: #d29922;
            --danger-color: #f85149;
            --shadow: 0 1px 3px rgba(0,0,0,0.5), 0 1px 2px rgba(0,0,0,0.4);
            --shadow-hover: 0 3px 6px rgba(0,0,0,0.6), 0 3px 6px rgba(0,0,0,0.5);
        }

        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', sans-serif; 
            margin: 0; 
            padding: 0;
            background: var(--bg-primary);
            color: var(--text-primary);
            transition: background-color 0.3s, color 0.3s;
        }

        .header { 
            background: var(--bg-secondary); 
            padding: 16px 0;
            border-bottom: 1px solid var(--border-primary);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            margin: 0;
            font-size: 20px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .nav { 
            display: flex;
            gap: 8px;
        }

        .nav a { 
            text-decoration: none; 
            color: var(--text-secondary);
            font-weight: 500;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 14px;
            transition: background-color 0.2s, color 0.2s;
        }

        .nav a:hover {
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }

        .nav a.active {
            background: var(--accent-color);
            color: white;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 16px;
        }

        .theme-toggle {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-primary);
            border-radius: 6px;
            padding: 8px 12px;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: background-color 0.2s;
        }

        .theme-toggle:hover {
            background: var(--bg-secondary);
        }

        .logout-btn {
            color: var(--danger-color) !important;
        }

        .logout-btn:hover {
            background: rgba(220, 53, 69, 0.1) !important;
        }

        .database-overview {
            background: var(--bg-secondary);
            padding: 24px;
            border-radius: 6px;
            border: 1px solid var(--border-primary);
            margin-bottom: 20px;
            box-shadow: var(--shadow);
        }

        .section-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: var(--bg-tertiary);
            padding: 16px;
            border-radius: 6px;
            border: 1px solid var(--border-primary);
            text-align: center;
        }

        .stat-number {
            font-size: 24px;
            font-weight: 600;
            color: var(--accent-color);
            margin: 8px 0;
        }

        .stat-label {
            font-size: 14px;
            color: var(--text-secondary);
        }

        .table-section {
            background: var(--bg-secondary);
            padding: 24px;
            border-radius: 6px;
            border: 1px solid var(--border-primary);
            margin-bottom: 24px;
            box-shadow: var(--shadow);
        }

        .table-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .table-title {
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .table-count {
            background: var(--accent-color);
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }

        .table-container {
            overflow-x: auto;
            border: 1px solid var(--border-primary);
            border-radius: 6px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        th {
            background: var(--bg-tertiary);
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 1px solid var(--border-primary);
            color: var(--text-secondary);
        }

        td {
            padding: 12px;
            border-bottom: 1px solid var(--border-primary);
        }

        tr:hover {
            background: var(--bg-tertiary);
        }

        .column-type {
            font-size: 12px;
            color: var(--text-tertiary);
            font-family: monospace;
        }

        .empty-state {
            padding: 40px 20px;
            text-align: center;
            color: var(--text-tertiary);
        }

        .empty-state h3 {
            margin: 0 0 8px 0;
            font-size: 18px;
            font-weight: 600;
        }

        .empty-state p {
            margin: 0;
            font-size: 14px;
        }

        .json-view {
            background: var(--bg-tertiary);
            padding: 12px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
        }

        .tabs {
            display: flex;
            border-bottom: 1px solid var(--border-primary);
            margin-bottom: 16px;
        }

        .tab {
            padding: 8px 16px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            color: var(--text-secondary);
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }

        .tab.active {
            color: var(--accent-color);
            border-bottom: 2px solid var(--accent-color);
        }

        .tab:hover {
            color: var(--text-primary);
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .search-box {
            margin-bottom: 16px;
        }

        .search-input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--border-primary);
            border-radius: 6px;
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 14px;
        }

        .search-input:focus {
            border-color: var(--accent-color);
            outline: none;
            box-shadow: 0 0 0 3px rgba(3, 102, 214, 0.3);
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <div class="header-content">
                <h1>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M3 5v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2zm16 14H5V5h14v14zM7 7h10v2H7V7zm0 4h10v2H7v-2zm0 4h7v2H7v-2z"/>
                    </svg>
                    База данных - Полная информация
                </h1>
                <div style="display: flex; align-items: center; gap: 16px;">
                    <button class="theme-toggle" id="themeToggle">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/>
                        </svg>
                        Тема
                    </button>
                    <div class="nav">
                        <a href="/dashboard">📊 Дашборд</a>
                        <a href="/tickets">🎫 Тикеты</a>
                        <a href="/users">👥 Пользователи</a>
                        <a href="/database" class="active">🗃️ База данных</a>
                        <a href="/logout" class="logout-btn">🚪 Выйти</a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="container">
        <!-- Обзор базы данных -->
        <div class="database-overview">
            <h2 class="section-title">📊 Обзор базы данных</h2>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{{ db_stats.total_tables }}</div>
                    <div class="stat-label">Таблиц в БД</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ db_stats.total_records }}</div>
                    <div class="stat-label">Всего записей</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ db_stats.total_users }}</div>
                    <div class="stat-label">Пользователей</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ db_stats.total_tickets }}</div>
                    <div class="stat-label">Тикетов</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ db_stats.total_messages }}</div>
                    <div class="stat-label">Сообщений</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ db_stats.total_media }}</div>
                    <div class="stat-label">Медиафайлов</div>
                </div>
            </div>
        </div>

        <!-- Поиск по базе данных -->
        <div class="database-overview">
            <h2 class="section-title">🔍 Поиск по базе данных</h2>
            <div class="search-box">
                <input type="text" class="search-input" id="searchInput" placeholder="Введите текст для поиска по всем таблицам...">
            </div>
        </div>

        <!-- Список таблиц -->
        {% for table_name, table_info in db_info.items() %}
        <div class="table-section">
            <div class="table-header">
                <div class="table-title">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M3 17h18c.55 0 1-.45 1-1s-.45-1-1-1H3c-.55 0-1 .45-1 1s.45 1 1 1zm0-4h18c.55 0 1-.45 1-1s-.45-1-1-1H3c-.55 0-1 .45-1 1s.45 1 1 1zm0-4h18c.55 0 1-.45 1-1s-.45-1-1-1H3c-.55 0-1 .45-1 1s.45 1 1 1zM3 7c0 .55.45 1 1 1h18c.55 0 1-.45 1-1s-.45-1-1-1H4c-.55 0-1 .45-1 1z"/>
                    </svg>
                    {{ table_name }}
                </div>
                <div class="table-count">{{ table_info.count }} записей</div>
            </div>

            <div class="tabs">
                <div class="tab active" data-tab="structure-{{ table_name }}">Структура</div>
                <div class="tab" data-tab="data-{{ table_name }}">Данные</div>
                {% if table_name == 'support_tickets' %}
                <div class="tab" data-tab="stats-{{ table_name }}">Статистика</div>
                {% endif %}
            </div>

            <!-- Структура таблицы -->
            <div class="tab-content active" id="structure-{{ table_name }}">
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Имя столбца</th>
                                <th>Тип данных</th>
                                <th>Размер</th>
                                <th>NULL</th>
                                <th>Ключ</th>
                                <th>По умолчанию</th>
                                <th>Дополнительно</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for column in table_info.columns %}
                            <tr>
                                <td><strong>{{ column[1] }}</strong></td>
                                <td><code class="column-type">{{ column[2] }}</code></td>
                                <td>{{ column[3] or '-' }}</td>
                                <td>{{ 'YES' if column[4] else 'NO' }}</td>
                                <td>{{ column[5] or '-' }}</td>
                                <td>{{ column[6] or 'NULL' }}</td>
                                <td>{{ column[7] or '-' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Данные таблицы -->
            <div class="tab-content" id="data-{{ table_name }}">
                {% if table_info.data %}
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                {% for column in table_info.columns %}
                                <th>{{ column[1] }}</th>
                                {% endfor %}
                            </tr>
                        </thead>
                        <tbody>
                            {% for row in table_info.data %}
                            <tr>
                                {% for value in row %}
                                <td>
                                    {% if value is none %}
                                        <span style="color: var(--text-tertiary); font-style: italic;">NULL</span>
                                    {% elif value is string and value|length > 100 %}
                                        {{ value[:100] }}...
                                    {% elif value is mapping %}
                                        <div class="json-view">{{ value | tojson }}</div>
                                    {% else %}
                                        {{ value }}
                                    {% endif %}
                                </td>
                                {% endfor %}
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <div class="empty-state">
                    <h3>😔 Нет данных</h3>
                    <p>Таблица {{ table_name }} не содержит записей</p>
                </div>
                {% endif %}
            </div>

            <!-- Статистика для таблицы тикетов -->
            {% if table_name == 'support_tickets' %}
            <div class="tab-content" id="stats-{{ table_name }}">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{{ table_info.stats.open or 0 }}</div>
                        <div class="stat-label">Открытых тикетов</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ table_info.stats.in_progress or 0 }}</div>
                        <div class="stat-label">Тикетов в работе</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ table_info.stats.resolved or 0 }}</div>
                        <div class="stat-label">Решенных тикетов</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ table_info.stats.avg_response_time or 0 }}</div>
                        <div class="stat-label">Среднее время ответа (ч)</div>
                    </div>
                </div>
                
                {% if table_info.stats.by_type %}
                <h4 style="margin: 20px 0 12px 0;">Распределение по типам:</h4>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Тип тикета</th>
                                <th>Количество</th>
                                <th>Процент</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for type, count in table_info.stats.by_type.items() %}
                            <tr>
                                <td>{{ type }}</td>
                                <td>{{ count }}</td>
                                <td>{{ "%.1f"|format((count / table_info.count) * 100) }}%</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% endif %}
            </div>
            {% endif %}
        </div>
        {% endfor %}

        <!-- SQL-запросы -->
        <div class="table-section">
            <div class="table-header">
                <div class="table-title">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M3 17h18c.55 0 1-.45 1-1s-.45-1-1-1H3c-.55 0-1 .45-1 1s.45 1 1 1zm0-4h18c.55 0 1-.45 1-1s-.45-1-1-1H3c-.55 0-1 .45-1 1s.45 1 1 1zm0-4h18c.55 0 1-.45 1-1s-.45-1-1-1H3c-.55 0-1 .45-1 1s.45 1 1 1zM3 7c0 .55.45 1 1 1h18c.55 0 1-.45 1-1s-.45-1-1-1H4c-.55 0-1 .45-1 1z"/>
                    </svg>
                    SQL-запросы
                </div>
            </div>
            
            <div style="margin-bottom: 16px;">
                <textarea id="sqlQuery" placeholder="Введите SQL-запрос..." style="width: 100%; height: 100px; padding: 12px; border: 1px solid var(--border-primary); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-family: monospace;"></textarea>
            </div>
            <div>
                <button class="theme-toggle" onclick="executeQuery()" style="background: var(--accent-color); color: white;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                    Выполнить запрос
                </button>
            </div>
            <div id="queryResult" style="margin-top: 16px;"></div>
        </div>
    </div>

    <script>
        // Функция для переключения темы
        function toggleTheme() {
            const body = document.body;
            const themeToggle = document.getElementById('themeToggle');
            
            if (body.classList.contains('dark-theme')) {
                body.classList.remove('dark-theme');
                localStorage.setItem('theme', 'light');
                themeToggle.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/>
                    </svg>
                    Тема
                `;
            } else {
                body.classList.add('dark-theme');
                localStorage.setItem('theme', 'dark');
                themeToggle.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 9c1.65 0 3 1.35 3 3s-1.35 3-3 3-3-1.35-3-3 1.35-3 3-3z"/>
                        <path d="M20 8.69V4h-4.69L12 .69 8.69 4H4v4.69L.69 12 4 15.31V20h4.69L12 23.31 15.31 20H20v-4.69L23.31 12 20 8.69zm-2 5.79V18h-3.52L12 20.48 9.52 18H6v-3.52L3.52 12 6 9.52V6h3.52L12 3.52 14.48 6H18v3.52L20.48 12 18 14.48z"/>
                    </svg>
                    Тема
                `;
            }
        }

        // Применение сохраненной темы при загрузке
        document.addEventListener('DOMContentLoaded', function() {
            const savedTheme = localStorage.getItem('theme');
            const themeToggle = document.getElementById('themeToggle');
            
            if (savedTheme === 'dark') {
                document.body.classList.add('dark-theme');
                themeToggle.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 9c1.65 0 3 1.35 3 3s-1.35 3-3 3-3-1.35-3-3 1.35-3 3-3z"/>
                        <path d="M20 8.69V4h-4.69L12 .69 8.69 4H4v4.69L.69 12 4 15.31V20h4.69L12 23.31 15.31 20H20v-4.69L23.31 12 20 8.69zm-2 5.79V18h-3.52L12 20.48 9.52 18H6v-3.52L3.52 12 6 9.52V6h3.52L12 3.52 14.48 6H18v3.52L20.48 12 18 14.48z"/>
                    </svg>
                    Тема
                `;
            }
            
            themeToggle.addEventListener('click', toggleTheme);

            // Обработчики для вкладок
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', function() {
                    const tabId = this.getAttribute('data-tab');
                    const parentSection = this.closest('.table-section');
                    
                    // Деактивируем все вкладки и контенты в этой секции
                    parentSection.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    parentSection.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    
                    // Активируем текущую вкладку и контент
                    this.classList.add('active');
                    document.getElementById(tabId).classList.add('active');
                });
            });

            // Поиск по таблицам
            document.getElementById('searchInput').addEventListener('input', function() {
                const searchTerm = this.value.toLowerCase();
                
                document.querySelectorAll('.table-section').forEach(section => {
                    let hasMatch = false;
                    
                    // Поиск в заголовках таблиц
                    const tableTitle = section.querySelector('.table-title').textContent.toLowerCase();
                    if (tableTitle.includes(searchTerm)) {
                        hasMatch = true;
                    }
                    
                    // Поиск в данных таблиц
                    section.querySelectorAll('td').forEach(cell => {
                        if (cell.textContent.toLowerCase().includes(searchTerm)) {
                            hasMatch = true;
                            // Подсветка совпадений
                            const text = cell.textContent;
                            const regex = new RegExp(`(${searchTerm})`, 'gi');
                            cell.innerHTML = text.replace(regex, '<mark style="background: yellow; color: black;">$1</mark>');
                        }
                    });
                    
                    // Показать/скрыть секцию на основе результатов поиска
                    section.style.display = hasMatch || searchTerm === '' ? 'block' : 'none';
                });
            });
        });

        // Функция выполнения SQL-запроса
        function executeQuery() {
            const query = document.getElementById('sqlQuery').value;
            const resultDiv = document.getElementById('queryResult');
            
            if (!query.trim()) {
                resultDiv.innerHTML = '<div class="error" style="padding: 12px; background: rgba(220, 53, 69, 0.1); color: var(--danger-color); border-radius: 6px;">Введите SQL-запрос</div>';
                return;
            }
            
            resultDiv.innerHTML = '<div style="padding: 12px; background: rgba(3, 102, 214, 0.1); color: var(--accent-color); border-radius: 6px;">Выполнение запроса...</div>';
            
            fetch('/api/database/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (data.results && data.results.length > 0) {
                        let html = '<div class="table-container"><table><thead><tr>';
                        
                        // Заголовки таблицы
                        Object.keys(data.results[0]).forEach(key => {
                            html += `<th>${key}</th>`;
                        });
                        html += '</tr></thead><tbody>';
                        
                        // Данные
                        data.results.forEach(row => {
                            html += '<tr>';
                            Object.values(row).forEach(value => {
                                html += `<td>${value !== null ? value : '<span style="color: var(--text-tertiary); font-style: italic;">NULL</span>'}</td>`;
                            });
                            html += '</tr>';
                        });
                        
                        html += '</tbody></table></div>';
                        resultDiv.innerHTML = html;
                    } else {
                        resultDiv.innerHTML = '<div class="success" style="padding: 12px; background: rgba(40, 167, 69, 0.1); color: var(--success-color); border-radius: 6px;">Запрос выполнен успешно. Нет данных для отображения.</div>';
                    }
                } else {
                    resultDiv.innerHTML = `<div class="error" style="padding: 12px; background: rgba(220, 53, 69, 0.1); color: var(--danger-color); border-radius: 6px;">Ошибка: ${data.error}</div>`;
                }
            })
            .catch(error => {
                resultDiv.innerHTML = `<div class="error" style="padding: 12px; background: rgba(220, 53, 69, 0.1); color: var(--danger-color); border-radius: 6px;">Ошибка выполнения: ${error}</div>`;
            });
        }
    </script>
</body>
</html>''')

if __name__ == '__main__':
    # Инициализируем базу данных
    init_db()
    
    # Создаем базовые шаблоны если их нет
    if not os.path.exists('templates'):
        create_basic_templates()
    
    print("🚀 Запуск расширенной админ-панели...")
    print("📸 Функционал: просмотр изображений, общение с пользователями, управление пользователями")
    print("🗃️ НОВЫЙ ФУНКЦИОНАЛ: Просмотр всей информации базы данных")
    print("🌐 Адрес: http://localhost:5000")
    print("🔑 Логин: admin / admin123")
    
    # Запускаем на всех интерфейсах порт 5000
    app.run(debug=True, host='0.0.0.0', port=5000)

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import pysqlite3 as sqlite3
import os
import hashlib
import requests
import json
from datetime import datetime

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

# Инициализация Flask приложения
app = Flask(__name__)
app.secret_key = 'admin-secret-key-12345-change-in-production'

# Настройки
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
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
        if response.status_code == 200:
            # Сохраняем сообщение в базу
            save_message(user_id, message, 'text', True)
            return True, "Сообщение отправлено"
        else:
            error_msg = f"Ошибка Telegram API: {response.status_code}"
            try:
                error_data = response.json()
                error_msg = f"Ошибка Telegram API: {error_data.get('description', 'Unknown error')}"
            except:
                pass
            return False, error_msg
    except Exception as e:
        return False, f"Ошибка отправки: {str(e)}"

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
    # users.html (нужно создать)

    # users.html
    with open(os.path.join(templates_dir, 'users.html'), 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html>
<head>
    <title>Пользователи</title>
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
        .user-card {
            background: white;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .user-stats {
            display: flex;
            gap: 20px;
            margin-top: 10px;
        }
        .stat {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            text-align: center;
            flex: 1;
        }
        .user-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .user-actions {
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>👥 Пользователи бота</h1>
            <div class="nav">
                <a href="/dashboard">📊 Дашборд</a>
                <a href="/tickets">🎫 Тикеты</a>
                <a href="/users">👥 Пользователи</a>
                <a href="/logout" style="color: #ff4444;">🚪 Выйти</a>
            </div>
        </div>
    </div>

    <div class="container">
        {% for user in users %}
        <div class="user-card">
            <div class="user-info">
                <div>
                    <h3>{{ user.first_name }} 
                        {% if user.username %}
                        <small>(@{{ user.username }})</small>
                        {% endif %}
                    </h3>
                    <p><strong>ID:</strong> {{ user.user_id }}</p>
                    <p><strong>Зарегистрирован:</strong> {{ user.registration_date }}</p>
                    <p><strong>Последняя активность:</strong> {{ user.last_activity }}</p>
                </div>
            </div>
            <div class="user-stats">
                <div class="stat">
                    <strong>💬 Сообщения</strong>
                    <div>{{ user.message_count }}</div>
                </div>
                <div class="stat">
                    <strong>🎫 Тикеты</strong>
                    <div>{{ user.ticket_count }}</div>
                </div>
            </div>
            <div class="user-actions">
                <a href="/tickets?user_id={{ user.user_id }}">📋 Показать тикеты</a>
            </div>
        </div>
        {% else %}
        <div style="background: white; padding: 40px; text-align: center; border-radius: 8px;">
            <h3>😔 Пользователей нет</h3>
            <p>Пока никто не использовал бота</p>
        </div>
        {% endfor %}
    </div>
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
    print("🌐 Адрес: http://localhost:5000")
    print("🔑 Логин: admin / admin123")
    
    # Запускаем на всех интерфейсах порт 5000
    app.run(debug=True, host='0.0.0.0', port=5000)

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database import get_all_tickets, update_ticket_status, get_system_stats, init_db
import pysqlite3 as sqlite3
import os
import hashlib

app = Flask(__name__)
app.secret_key = 'admin-secret-key-12345'

# Хэширование паролей
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Администраторы
ADMIN_CREDENTIALS = {
    'admin': hash_password('admin123')
}

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
    print(f"📊 Статистика для дашборда: {stats}")
    
    return render_template('dashboard.html', 
                         stats=stats,
                         recent_tickets=stats.get('recent_tickets', []))

@app.route('/tickets')
def tickets_page():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    status = request.args.get('status', 'all')
    tickets = get_all_tickets(status if status != 'all' else None)
    
    print(f"🎫 Запрошены тикеты со статусом '{status}': найдено {len(tickets)}")
    
    return render_template('tickets.html', tickets=tickets, status=status)

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

@app.route('/api/stats')
def api_stats():
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    stats = get_system_stats()
    return jsonify(stats)

@app.route('/debug/db')
def debug_db():
    """Страница отладки базы данных"""
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Получаем информацию о таблицах
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    db_info = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        db_info[table_name] = {
            'count': count,
            'columns': columns
        }
    
    conn.close()
    
    return render_template('debug_db.html', db_info=db_info)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Инициализируем базу данных
    print("🚀 Инициализация админ-панели...")
    init_db()
    
    # Запускаем на всех интерфейсах порт 5000
    print("🌐 Запуск Flask приложения...")
    app.run(debug=True, host='0.0.0.0', port=5000)

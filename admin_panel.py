from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from database import get_all_tickets, update_ticket_status, get_system_stats, init_db
from database import get_ticket_by_id, get_media_files_by_ticket, get_conversation_messages
from telegram_utils import send_telegram_message
import pysqlite3 as sqlite3
import os
import hashlib

app = Flask(__name__)
app.secret_key = 'admin-secret-key-12345'

# Настройки
UPLOAD_FOLDER = 'media'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
    open_tickets = get_all_tickets('open')
    
    return render_template('dashboard.html', 
                         stats=stats,
                         open_tickets=open_tickets)

@app.route('/tickets')
def tickets_page():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    status = request.args.get('status', 'all')
    if status == 'all':
        tickets = get_all_tickets()
    else:
        tickets = get_all_tickets(status)
    
    return render_template('tickets.html', tickets=tickets, status=status)

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
                         conversation=conversation)

@app.route('/media/<path:filename>')
def serve_media(filename):
    if 'admin' not in session:
        return "Unauthorized", 401
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Инициализируем базу данных
    init_db()
    
    # Создаем папку для медиа если её нет
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    print("🚀 Запуск расширенной админ-панели...")
    print("📸 Функционал: просмотр изображений, общение с пользователями")
    print("🌐 Адрес: http://localhost:5000")
    
    # Запускаем на всех интерфейсах порт 5000
    app.run(debug=True, host='0.0.0.0', port=5000)

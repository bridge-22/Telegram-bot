# telegram_bot/admin_panel.py
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pysqlite3 as sqlite3
import os
import hashlib
from database import get_all_tickets, update_ticket_status, get_system_stats, init_db

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

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Инициализируем базу данных
    init_db()
    
    # Запускаем на всех интерфейсах порт 5000
    app.run(debug=True, host='0.0.0.0', port=5000)

import pysqlite3 as sqlite3
import datetime
from typing import Optional, List, Dict, Any

def get_connection():
    """Создание соединения с базой данных"""
    return sqlite3.connect('bot_database.db', check_same_thread=False)

def init_db():
    """Инициализация базы данных"""
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
    
    # Таблица для администраторов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            permissions TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_user(user_id: int, first_name: str, username: Optional[str] = None):
    """Сохранение/обновление пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_activity)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, username, first_name))
    conn.commit()
    conn.close()

def save_message(user_id: int, message_text: str, message_type: str = 'text'):
    """Сохранение сообщения"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (user_id, message_text, message_type)
        VALUES (?, ?, ?)
    ''', (user_id, message_text, message_type))
    conn.commit()
    conn.close()

def create_support_ticket(user_id: int, description: str, ticket_type: str) -> int:
    """Создание тикета поддержки"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO support_tickets (user_id, description, ticket_type)
        VALUES (?, ?, ?)
    ''', (user_id, description, ticket_type))
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id

def get_user_stats(user_id: int) -> Dict[str, Any]:
    """Получение статистики пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM messages WHERE user_id = ?', (user_id,))
    message_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM support_tickets WHERE user_id = ?', (user_id,))
    ticket_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'message_count': message_count,
        'ticket_count': ticket_count
    }

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение информации о пользователе"""
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

# Функции для административной панели
def get_all_tickets(status: str = None) -> List[Dict[str, Any]]:
    """Получение всех тикетов (для админки)"""
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
    """Обновление статуса тикета (для админки)"""
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

def get_system_stats() -> Dict[str, Any]:
    """Получение системной статистики для админки"""
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
    
    conn.close()
    
    return {
        'total_users': total_users,
        'open_tickets': open_tickets,
        'resolved_tickets': resolved_tickets,
        'total_messages': total_messages
    }

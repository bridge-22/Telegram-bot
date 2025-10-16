from flask import Flask, jsonify
import socket
import sqlite3
import os

app = Flask(__name__)

def get_local_ip():
    """Получение локального IP адреса"""
    try:
        # Создаем временное соединение чтобы получить локальный IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "Не удалось определить IP"

@app.route('/')
def home():
    local_ip = get_local_ip()
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Debug Admin</title></head>
    <body>
        <h1>🚀 Админ-панель запущена!</h1>
        <h2>Доступ по адресам:</h2>
        <ul>
            <li><a href="http://localhost:5000">http://localhost:5000</a></li>
            <li><a href="http://127.0.0.1:5000">http://127.0.0.1:5000</a></li>
            <li><a href="http://{local_ip}:5000">http://{local_ip}:5000</a></li>
        </ul>
        <h3>Информация о сервере:</h3>
        <p>Локальный IP: {local_ip}</p>
        <p>Хостнейм: {socket.gethostname()}</p>
    </body>
    </html>
    '''

@app.route('/api/health')
def health():
    return jsonify({
        "status": "running",
        "local_ip": get_local_ip(),
        "hostname": socket.gethostname()
    })

if __name__ == '__main__':
    local_ip = get_local_ip()
    print("=" * 50)
    print("🚀 Запуск админ-панели...")
    print(f"📡 Локальный IP: {local_ip}")
    print(f"🔧 Порт: 5000")
    print("=" * 50)
    print(f"📋 Доступные адреса:")
    print(f"   http://localhost:5000")
    print(f"   http://127.0.0.1:5000") 
    print(f"   http://{local_ip}:5000")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)

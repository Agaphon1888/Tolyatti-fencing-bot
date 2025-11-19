import sqlite3
from datetime import datetime
import logging
from config import ADMINS

logger = logging.getLogger(__name__)

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    # Таблица пользовательских сессий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            district TEXT,
            base TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица запросов на тренировки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            district TEXT,
            base TEXT,
            child_info TEXT,
            contact TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица статистики
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT,
            user_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица административных действий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            target_user_id INTEGER,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

def save_user_session(user_id, username, first_name, last_name, district=None, base=None):
    """Сохранение сессии пользователя"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO user_sessions 
        (user_id, username, first_name, last_name, district, base, last_activity)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, username, first_name, last_name, district, base))
    
    conn.commit()
    conn.close()

def log_user_action(user_id, action_type):
    """Логирование действий пользователя"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO bot_statistics (action_type, user_id)
        VALUES (?, ?)
    ''', (action_type, user_id))
    
    conn.commit()
    conn.close()

def log_admin_action(admin_id, action, target_user_id=None, details=None):
    """Логирование действий администратора"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO admin_actions (admin_id, action, target_user_id, details)
        VALUES (?, ?, ?, ?)
    ''', (admin_id, action, target_user_id, details))
    
    conn.commit()
    conn.close()

def get_statistics():
    """Получение статистики бота"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    # Общее количество пользователей
    cursor.execute('SELECT COUNT(*) FROM user_sessions')
    total_users = cursor.fetchone()[0]
    
    # Активные пользователи (за последние 30 дней)
    cursor.execute('''
        SELECT COUNT(*) FROM user_sessions 
        WHERE last_activity > datetime('now', '-30 days')
    ''')
    active_users = cursor.fetchone()[0]
    
    # Количество действий по типам
    cursor.execute('''
        SELECT action_type, COUNT(*) FROM bot_statistics 
        GROUP BY action_type
    ''')
    actions_count = dict(cursor.fetchall())
    
    # Последние действия
    cursor.execute('''
        SELECT action_type, timestamp FROM bot_statistics 
        ORDER BY timestamp DESC LIMIT 10
    ''')
    recent_actions = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'actions_count': actions_count,
        'recent_actions': recent_actions
    }

def get_user_info(user_id):
    """Получение информации о пользователе"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM user_sessions WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    
    cursor.execute('''
        SELECT action_type, COUNT(*) FROM bot_statistics 
        WHERE user_id = ? GROUP BY action_type
    ''', (user_id,))
    user_actions = dict(cursor.fetchall())
    
    conn.close()
    
    return {
        'user_data': user_data,
        'user_actions': user_actions
    }

def broadcast_message(message, exclude_admins=False):
    """Получение списка пользователей для рассылки"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    if exclude_admins:
        # Исключаем администраторов из рассылки
        placeholders = ','.join('?' * len(ADMINS))
        query = f'''
            SELECT user_id FROM user_sessions 
            WHERE user_id NOT IN ({placeholders})
        '''
        cursor.execute(query, ADMINS)
    else:
        # Все пользователи
        cursor.execute('SELECT user_id FROM user_sessions')
    
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return users

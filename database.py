import sqlite3
from datetime import datetime
import logging

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

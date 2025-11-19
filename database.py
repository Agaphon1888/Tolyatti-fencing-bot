import sqlite3
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

# Импортируем ADMINS с обработкой ошибок
try:
    from config import ADMINS
except ImportError:
    ADMINS = []
    logger.warning("ADMINS not found in config, using empty list")

def get_db_connection():
    """Создает соединение с базой данных"""
    # На Render.com используем абсолютный путь
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация базы данных"""
    try:
        conn = get_db_connection()
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
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")

def save_user_session(user_id, username, first_name, last_name, district=None, base=None):
    """Сохранение сессии пользователя"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_sessions 
            (user_id, username, first_name, last_name, district, base, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, username, first_name, last_name, district, base))
        
        conn.commit()
        conn.close()
        logger.debug(f"💾 Сохранена сессия пользователя {user_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения сессии пользователя {user_id}: {e}")

def log_user_action(user_id, action_type):
    """Логирование действий пользователя"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bot_statistics (action_type, user_id)
            VALUES (?, ?)
        ''', (action_type, user_id))
        
        conn.commit()
        conn.close()
        logger.debug(f"📊 Залогировано действие {action_type} для пользователя {user_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка логирования действия пользователя {user_id}: {e}")

def log_admin_action(admin_id, action, target_user_id=None, details=None):
    """Логирование действий администратора"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO admin_actions (admin_id, action, target_user_id, details)
            VALUES (?, ?, ?, ?)
        ''', (admin_id, action, target_user_id, details))
        
        conn.commit()
        conn.close()
        logger.debug(f"🛠 Залогировано действие администратора {admin_id}: {action}")
    except Exception as e:
        logger.error(f"❌ Ошибка логирования действия администратора {admin_id}: {e}")

def get_statistics():
    """Получение статистики бота"""
    try:
        conn = get_db_connection()
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
        actions_result = cursor.fetchall()
        actions_count = dict(actions_result) if actions_result else {}
        
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
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        return {
            'total_users': 0,
            'active_users': 0,
            'actions_count': {},
            'recent_actions': []
        }

def get_user_info(user_id):
    """Получение информации о пользователе"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user_sessions WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()
        
        cursor.execute('''
            SELECT action_type, COUNT(*) FROM bot_statistics 
            WHERE user_id = ? GROUP BY action_type
        ''', (user_id,))
        user_actions_result = cursor.fetchall()
        user_actions = dict(user_actions_result) if user_actions_result else {}
        
        conn.close()
        
        return {
            'user_data': user_data,
            'user_actions': user_actions
        }
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации о пользователе {user_id}: {e}")
        return {
            'user_data': None,
            'user_actions': {}
        }

def broadcast_message(message, exclude_admins=False):
    """Получение списка пользователей для рассылки"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if exclude_admins and ADMINS:
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
        
        logger.debug(f"📢 Получен список пользователей для рассылки: {len(users)} пользователей")
        return users
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка для рассылки: {e}")
        return []

def add_training_request(user_id, district, base, child_info, contact):
    """Добавление заявки на тренировку"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO training_requests (user_id, district, base, child_info, contact)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, district, base, child_info, contact))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Добавлена заявка на тренировку от пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления заявки на тренировку: {e}")
        return False

def get_training_requests(status=None):
    """Получение заявок на тренировки"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM training_requests 
                WHERE status = ? 
                ORDER BY created_at DESC
            ''', (status,))
        else:
            cursor.execute('''
                SELECT * FROM training_requests 
                ORDER BY created_at DESC
            ''')
        
        requests = cursor.fetchall()
        conn.close()
        
        return requests
    except Exception as e:
        logger.error(f"❌ Ошибка получения заявок на тренировки: {e}")
        return []

def update_training_request_status(request_id, status):
    """Обновление статуса заявки на тренировку"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE training_requests 
            SET status = ? 
            WHERE id = ?
        ''', (status, request_id))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Обновлен статус заявки {request_id} на '{status}'")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления статуса заявки {request_id}: {e}")
        return False

def get_user_count():
    """Получение общего количества пользователей"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM user_sessions')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    except Exception as e:
        logger.error(f"❌ Ошибка получения количества пользователей: {e}")
        return 0

def get_recent_users(days=7):
    """Получение пользователей, активных за последние N дней"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM user_sessions 
            WHERE last_activity > datetime('now', ?)
        ''', (f'-{days} days',))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"❌ Ошибка получения недавних пользователей: {e}")
        return 0

# Автоматически инициализируем базу данных при импорте модуля
init_db()

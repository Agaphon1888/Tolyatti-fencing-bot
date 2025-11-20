import os
import logging
from flask import Flask, request, jsonify
import requests
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Конфигурация
ORG_INFO = {
    'full_name': 'Автономная некоммерческая организация "Тольяттинская федерация фехтования"',
    'short_name': 'АНО "Тольяттинская федерация фехтования"',
    'inn': '6320267029',
    'kpp': '632001001',
    'ogrn': '1146300002793',
    'account': '40703810212300001063',
    'bank': 'ОАО АКБ "Авангард"',
    'bik': '044525201',
    'correspondent_account': '3010181000000000201'
}

DISTRICTS_INFO = {
    'central': {
        'name': 'Центральный район',
        'chat_link': 'https://t.me/+ls3LxVHjH680MDdi',
        'schedule': '''Пн - ОФП и фехтование 18:00
Ср - ОФП и фехтование 18:00
Сб - Фехтование 18:00''',
        'address': 'Ленина 58, школа 91, корпус Б, малый зал',
        'price': '2000 рублей в месяц'
    },
    'avtozavodsky': {
        'name': 'Автозаводский район',
        'chat_link': 'https://t.me/+IQpyrN7sq3c2ZjRi',
        'bases': {
            'volgar': {
                'name': 'Волгарь',
                'schedule': '''ПН: 16:00 средние и новички ОФП, 18:30 малыши и новички ОФП
ВТ: 15:00 средние и новички фехтование, 16:30 новички (новый зал)
СР: 17:15 новички все (новый зал)
ЧТ: 15:00 средние и новички фехтование, 16:30 новички (новый зал)
ПТ: 15:30 средние и новички фехтование
СБ: 16:30-18:00 новички все (новый зал)''',
                'address': 'ДС Волгарь, вход со стороны Веги, зал Фехтования'
            },
            'school69': {
                'name': 'Школа 69',
                'schedule': '''ПН: 15:30-16:30
ВТ: 16:00-18:00
СР: 15:30-16:30
ЧТ: 16:00-18:00
ПТ: 16:00-18:00
СБ: Боевая в волгаре (уточнить время)
ВСК: 12:00-14:00''',
                'address': '13 квартал, 40 лет Победы, 120, Музыкальный зал'
            },
            'school66': {
                'name': 'Школа 66',
                'schedule': 'Уточняется в чате района',
                'address': 'Уточняется в чате района'
            }
        },
        'price': '2000 рублей в месяц'
    },
    'komso': {
        'name': 'Комсомольский район',
        'chat_link': 'https://t.me/+jO5wcwUbxq0wMjgy',
        'schedule': '''Пн: 15:00 (ср/ст и новички), 17:00 (мл и новички)
Вт: 9:00 (2 смена новички), 15:00 (мл), 16:00 (ср/ст)
Ср: 16:00-18:00 ОФП
Чт: 9:00 (2 смена), 15:00 (ср/мл), 16:00 (ст), 17:00 (мл и новички)
Пт: 15:00 (ср/ст), 17:00 (мл)
Сб: 14:00 ОФП (мл и новички)''',
        'address': 'Мурысева 52а, вход со двора',
        'price': '2000 рублей в месяц'
    },
    'zhig': {
        'name': 'Жигулёвск',
        'chat_link': 'https://t.me/+b4YyZF5QXts1NTVi',
        'schedule': '''Ср: 16:30-18:00 ОФП
Чт: 16:00-17:30 фехтование
Сб: 15:30-17:00 фехтование и ОФП
Вск: 13:00-14:00 ОФП и фехтование''',
        'address': 'ДМО, Гидростроителей 10а',
        'price': '2000 рублей в месяц'
    }
}

DOCUMENTS_LIST = '''
📋 <b>Необходимые документы:</b>

• 4 фотографии 3x4
• Копия свидетельства о рождении или паспорта с пропиской
• Копия паспорта одного из родителей с пропиской
• Копия СНИЛС ребенка
• Копия ИНН ребенка
• Справка из школы
• Справка от педиатра, что здоров и может заниматься ФЕХТОВАНИЕМ
• Доверенности, согласия и заявления (бланки выдаются на месте)

⚠️ <b>Важно:</b> Документы можно принести после пробных тренировок!
'''

FAQ_TEXT = '''
❓ <b>Частые вопросы:</b>

<b>1. С чего начать?</b>
Выберите район, придите на пробную тренировку. Все необходимое для первой тренировки: сменная обувь, спортивная форма, вода.

<b>2. Когда нужно платить?</b>
Оплата производится после пробных тренировок, когда вы приняли решение заниматься.

<b>3. Нужно ли сразу приносить документы?</b>
Нет, документы можно принести в течение первых недель занятий.

<b>4. Сколько раз в неделю проходят тренировки?</b>
Новички обычно занимаются 3 раза в неделю, затем количество тренировок может увеличиваться.

<b>5. Можно ли поменять район/базу?</b>
Да, в течение пробного периода можно выбрать наиболее удобный вариант.
'''

# Функции для работы с Telegram API
def send_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    """Отправка сообщения через Telegram API"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ Message sent to {chat_id}")
            return True
        else:
            logger.error(f"❌ Failed to send message: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error sending message: {e}")
        return False

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode='HTML'):
    """Редактирование сообщения через Telegram API"""
    url = f"{TELEGRAM_API_URL}/editMessageText"
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Error editing message: {e}")
        return False

def answer_callback_query(callback_query_id, text=None):
    """Ответ на callback запрос"""
    url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
    payload = {
        'callback_query_id': callback_query_id
    }
    if text:
        payload['text'] = text
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Error answering callback: {e}")
        return False

# Клавиатуры
def get_main_menu_keyboard(is_admin=False):
    """Клавиатура главного меню"""
    keyboard = {
        'inline_keyboard': [
            [{'text': '🏃 Выбрать район', 'callback_data': 'main_districts'}],
            [{'text': '💳 Реквизиты оплаты', 'callback_data': 'main_payment'}],
            [{'text': '📋 Список документов', 'callback_data': 'main_documents'}],
            [{'text': '❓ Частые вопросы', 'callback_data': 'main_faq'}]
        ]
    }
    if is_admin:
        keyboard['inline_keyboard'].append([{'text': '🛠 Админ-панель', 'callback_data': 'admin_back'}])
    return keyboard

def get_districts_keyboard():
    """Клавиатура выбора района"""
    return {
        'inline_keyboard': [
            [{'text': 'Центральный район', 'callback_data': 'district_central'}],
            [{'text': 'Автозаводский район', 'callback_data': 'district_avtozavodsky'}],
            [{'text': 'Комсомольский район', 'callback_data': 'district_komso'}],
            [{'text': 'Жигулёвск', 'callback_data': 'district_zhig'}],
            [{'text': '◀️ Назад', 'callback_data': 'back_to_main'}]
        ]
    }

def get_back_to_main_keyboard():
    """Клавиатура с кнопкой назад"""
    return {
        'inline_keyboard': [
            [{'text': '🏠 В главное меню', 'callback_data': 'back_to_main'}]
        ]
    }

def get_admin_menu_keyboard():
    """Клавиатура админ-панели"""
    return {
        'inline_keyboard': [
            [{'text': '📊 Статистика', 'callback_data': 'admin_stats'}],
            [{'text': '📢 Рассылка', 'callback_data': 'admin_broadcast'}],
            [{'text': '👥 Поиск пользователя', 'callback_data': 'admin_search'}],
            [{'text': '🏠 Пользовательское меню', 'callback_data': 'back_to_main'}]
        ]
    }

# Обработчики команд
def handle_start_command(chat_id, user_id, username, first_name):
    """Обработчик команды /start"""
    logger.info(f"👤 User {user_id} started the bot")
    
    welcome_text = f"""
🤺 Добро пожаловать в <b>Тольяттинскую федерацию фехтования</b>, {first_name}!

Здесь вы можете:
• Выбрать удобный район для тренировок
• Узнать реквизиты для оплаты
• Получить список необходимых документов
• Найти ответы на частые вопросы

Выберите нужный раздел:
    """
    
    # Проверяем, является ли пользователь администратором
    admins_str = os.getenv('ADMINS', '')
    admins = [int(admin_id.strip()) for admin_id in admins_str.split(',') if admin_id.strip().isdigit()]
    is_admin = user_id in admins
    
    keyboard = get_main_menu_keyboard(is_admin)
    return send_message(chat_id, welcome_text, keyboard)

def handle_districts_selection(chat_id, message_id, district_key):
    """Обработчик выбора района"""
    district_info = DISTRICTS_INFO.get(district_key)
    if not district_info:
        return False
    
    if district_key == 'avtozavodsky':
        return handle_avtozavodsky_district(chat_id, message_id, district_info)
    
    message = format_district_info(district_info)
    keyboard = {
        'inline_keyboard': [
            [{'text': '💳 Реквизиты оплаты', 'callback_data': 'main_payment'}],
            [{'text': '📋 Документы', 'callback_data': 'main_documents'}],
            [{'text': '◀️ Выбрать другой район', 'callback_data': 'main_districts'}],
            [{'text': '🏠 В главное меню', 'callback_data': 'back_to_main'}]
        ]
    }
    
    if message_id:
        return edit_message(chat_id, message_id, message, keyboard)
    else:
        return send_message(chat_id, message, keyboard)

def handle_avtozavodsky_district(chat_id, message_id, district_info):
    """Обработчик Автозаводского района (выбор базы)"""
    keyboard = {
        'inline_keyboard': []
    }
    
    for base_key, base_info in district_info['bases'].items():
        keyboard['inline_keyboard'].append([{'text': base_info['name'], 'callback_data': f'base_{base_key}'}])
    
    keyboard['inline_keyboard'].append([{'text': '◀️ Назад к районам', 'callback_data': 'main_districts'}])
    
    message = "🏢 <b>Автозаводский район</b>\n\nВыберите удобную вам базу:"
    
    if message_id:
        return edit_message(chat_id, message_id, message, keyboard)
    else:
        return send_message(chat_id, message, keyboard)

def handle_base_selection(chat_id, message_id, base_key):
    """Обработчик выбора базы"""
    district_info = DISTRICTS_INFO['avtozavodsky']
    base_info = district_info['bases'].get(base_key)
    
    if not base_info:
        return False
    
    message = format_base_info(district_info, base_info)
    keyboard = {
        'inline_keyboard': [
            [{'text': '💳 Реквизиты оплаты', 'callback_data': 'main_payment'}],
            [{'text': '📋 Документы', 'callback_data': 'main_documents'}],
            [{'text': '◀️ Выбрать другую базу', 'callback_data': 'district_avtozavodsky'}],
            [{'text': '🏠 В главное меню', 'callback_data': 'back_to_main'}]
        ]
    }
    
    return edit_message(chat_id, message_id, message, keyboard)

def handle_payment_info(chat_id, message_id=None):
    """Обработчик информации об оплате"""
    message = format_payment_info()
    keyboard = get_back_to_main_keyboard()
    
    if message_id:
        return edit_message(chat_id, message_id, message, keyboard)
    else:
        return send_message(chat_id, message, keyboard)

def handle_documents_info(chat_id, message_id=None):
    """Обработчик информации о документах"""
    keyboard = get_back_to_main_keyboard()
    
    if message_id:
        return edit_message(chat_id, message_id, DOCUMENTS_LIST, keyboard)
    else:
        return send_message(chat_id, DOCUMENTS_LIST, keyboard)

def handle_faq_info(chat_id, message_id=None):
    """Обработчик FAQ"""
    keyboard = get_back_to_main_keyboard()
    
    if message_id:
        return edit_message(chat_id, message_id, FAQ_TEXT, keyboard)
    else:
        return send_message(chat_id, FAQ_TEXT, keyboard)

def handle_admin_panel(chat_id, message_id=None):
    """Обработчик админ-панели"""
    admins_str = os.getenv('ADMINS', '')
    admins = [int(admin_id.strip()) for admin_id in admins_str.split(',') if admin_id.strip().isdigit()]
    
    admin_text = f"""
🛠 <b>Панель администратора</b>

👑 Администраторов: {len(admins)}
Выберите действие:
    """
    
    keyboard = get_admin_menu_keyboard()
    
    if message_id:
        return edit_message(chat_id, message_id, admin_text, keyboard)
    else:
        return send_message(chat_id, admin_text, keyboard)

def handle_admin_stats(chat_id, message_id):
    """Обработчик статистики"""
    stats_text = """
📊 <b>Статистика бота</b>

👥 <b>Пользователи:</b>
• Всего: информация в разработке
• Активных: информация в разработке

🛠 <b>Админ-функции:</b>
• Рассылка: в разработке
• Поиск пользователя: в разработке
    """
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '◀️ Назад в админку', 'callback_data': 'admin_back'}]
        ]
    }
    
    return edit_message(chat_id, message_id, stats_text, keyboard)

def handle_admin_broadcast(chat_id, message_id):
    """Обработчик рассылки"""
    broadcast_text = """
📢 <b>Рассылка сообщений</b>

Функция рассылки находится в разработке.

В будущем здесь можно будет:
• Отправлять сообщения всем пользователям
• Отправлять сообщения только пользователям (без админов)
• Просматривать историю рассылок
    """
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '◀️ Назад в админку', 'callback_data': 'admin_back'}]
        ]
    }
    
    return edit_message(chat_id, message_id, broadcast_text, keyboard)

def handle_admin_search(chat_id, message_id):
    """Обработчик поиска пользователя"""
    search_text = """
👥 <b>Поиск пользователя</b>

Функция поиска пользователя находится в разработке.

В будущем здесь можно будет:
• Искать пользователей по ID, имени или username
• Просматривать статистику конкретного пользователя
• Отправлять сообщения конкретным пользователям
    """
    
    keyboard = {
        'inline_keyboard': [
            [{'text': '◀️ Назад в админку', 'callback_data': 'admin_back'}]
        ]
    }
    
    return edit_message(chat_id, message_id, search_text, keyboard)

# Функции форматирования
def format_district_info(district_info):
    return f"""
<b>{district_info['name']}</b>

📍 <b>Адрес:</b> {district_info['address']}

📅 <b>Расписание:</b>
{district_info['schedule']}

💬 <b>Чат для родителей:</b> {district_info['chat_link']}

💰 <b>Стоимость:</b> {district_info['price']}

👕 <b>С собой на тренировку:</b> сменные кроссовки для зала, белые носки, спортивная форма, бутылочка с водой

⚠️ <b>Важно:</b> пока не нужно платить и приносить документы! Все в процессе!
    """

def format_base_info(district_info, base_info):
    return f"""
<b>{district_info['name']} - {base_info['name']}</b>

📍 <b>Адрес:</b> {base_info['address']}

📅 <b>Расписание:</b>
{base_info['schedule']}

💬 <b>Чат для родителей:</b> {district_info['chat_link']}

💰 <b>Стоимость:</b> {district_info['price']}

👕 <b>С собой на тренировку:</b> сменные кроссовки для зала, белые носки, спортивная форма, бутылочка с водой

⚠️ <b>Важно:</b> пока не нужно платить и приносить документов! Все в процессе!
    """

def format_payment_info():
    return f"""
💳 <b>Реквизиты для оплаты</b>

🏛 <b>Полное наименование:</b> 
{ORG_INFO['full_name']}

📋 <b>Сокращенное:</b> 
{ORG_INFO['short_name']}

📊 <b>Реквизиты:</b>
ИНН: {ORG_INFO['inn']}
КПП: {ORG_INFO['kpp']}
ОГРН: {ORG_INFO['ogrn']}
Расчетный счет: {ORG_INFO['account']}
Банк: {ORG_INFO['bank']}
БИК: {ORG_INFO['bik']}
Корр. счет: {ORG_INFO['correspondent_account']}

💸 <b>Сумма:</b> 2000 рублей в месяц
📝 <b>Назначение платежа:</b> "Добровольное пожертвование от [ФИО ребенка]"

⚠️ <b>Важно:</b>
• Оплата производится после пробных тренировок
• В назначении платежа укажите ФИО ребенка
• Сохраните чек об оплате
• Квитанцию можно показать тренеру или отправить в чат группы
    """

# Flask маршруты
@app.route('/')
def home():
    return "🤺 Fencing Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/debug')
def debug():
    """Страница диагностики"""
    try:
        webhook_info = requests.get(f"{TELEGRAM_API_URL}/getWebhookInfo").json()
        return {
            "bot_token_set": bool(BOT_TOKEN),
            "webhook_info": webhook_info,
            "status": "running"
        }
    except Exception as e:
        return {"error": str(e)}

@app.route('/webhook', methods=['POST'])
def webhook():
    """Основной обработчик вебхуков от Telegram"""
    try:
        data = request.get_json()
        logger.info(f"📨 Received update: {data}")
        
        # Обрабатываем сообщения
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            username = message['from'].get('username', '')
            first_name = message['from'].get('first_name', '')
            
            # Проверяем права администратора
            admins_str = os.getenv('ADMINS', '')
            admins = [int(admin_id.strip()) for admin_id in admins_str.split(',') if admin_id.strip().isdigit()]
            is_admin = user_id in admins
            
            if 'text' in message:
                text = message['text']
                
                if text.startswith('/start'):
                    handle_start_command(chat_id, user_id, username, first_name)
                elif text.startswith('/payment'):
                    handle_payment_info(chat_id)
                elif text.startswith('/documents'):
                    handle_documents_info(chat_id)
                elif text.startswith('/faq'):
                    handle_faq_info(chat_id)
                elif text.startswith('/admin') and is_admin:
                    handle_admin_panel(chat_id)
                elif text.startswith('/stats') and is_admin:
                    # Временная реализация команды /stats
                    send_message(chat_id, "📊 Статистика бота:\n\nФункция в разработке. Используйте админ-панель для просмотра статистики.")
                else:
                    send_message(chat_id, "Используйте команду /start для начала работы")
        
        # Обрабатываем callback запросы
        elif 'callback_query' in data:
            callback_query = data['callback_query']
            callback_data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            message_id = callback_query['message']['message_id']
            user_id = callback_query['from']['id']
            
            # Проверяем права администратора для админ-функций
            admins_str = os.getenv('ADMINS', '')
            admins = [int(admin_id.strip()) for admin_id in admins_str.split(',') if admin_id.strip().isdigit()]
            is_admin = user_id in admins
            
            # Отвечаем на callback запрос
            answer_callback_query(callback_query['id'])
            
            # Обрабатываем различные callback данные
            if callback_data == 'back_to_main':
                handle_start_command(chat_id, user_id, '', '')
            
            elif callback_data == 'main_districts':
                keyboard = get_districts_keyboard()
                edit_message(chat_id, message_id, "🏃 <b>Выберите район:</b>\n\nПосле выбора района вы получите:\n• Адрес и расписание\n• Ссылку на чат родителей\n• Всю необходимую информацию", keyboard)
            
            elif callback_data.startswith('district_'):
                district_key = callback_data.replace('district_', '')
                handle_districts_selection(chat_id, message_id, district_key)
            
            elif callback_data.startswith('base_'):
                base_key = callback_data.replace('base_', '')
                handle_base_selection(chat_id, message_id, base_key)
            
            elif callback_data == 'main_payment':
                handle_payment_info(chat_id, message_id)
            
            elif callback_data == 'main_documents':
                handle_documents_info(chat_id, message_id)
            
            elif callback_data == 'main_faq':
                handle_faq_info(chat_id, message_id)
            
            # Обработка админ-панели
            elif callback_data == 'admin_back':
                if is_admin:
                    handle_admin_panel(chat_id, message_id)
                else:
                    send_message(chat_id, "⛔ У вас нет прав доступа к админ-панели.")
            
            elif callback_data == 'admin_stats':
                if is_admin:
                    handle_admin_stats(chat_id, message_id)
                else:
                    send_message(chat_id, "⛔ У вас нет прав доступа к этой функции.")
            
            elif callback_data == 'admin_broadcast':
                if is_admin:
                    handle_admin_broadcast(chat_id, message_id)
                else:
                    send_message(chat_id, "⛔ У вас нет прав доступа к этой функции.")
            
            elif callback_data == 'admin_search':
                if is_admin:
                    handle_admin_search(chat_id, message_id)
                else:
                    send_message(chat_id, "⛔ У вас нет прав доступа к этой функции.")
        
        return 'OK'
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return 'Error', 500

def self_ping():
    """Самопинг для поддержания активности"""
    def ping_loop():
        while True:
            try:
                response = requests.get("https://tolyatti-fencing-bot.onrender.com/health", timeout=10)
                logger.info(f"✅ Self-ping successful: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Self-ping failed: {e}")
            time.sleep(300)  # 5 минут
    
    thread = threading.Thread(target=ping_loop, daemon=True)
    thread.start()
    logger.info("🔄 Self-ping thread started")

# Установка вебхука при старте
if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE':
    try:
        webhook_url = f"https://tolyatti-fencing-bot.onrender.com/webhook"
        logger.info(f"🔧 Setting webhook to: {webhook_url}")
        
        # Даем время на запуск сервера
        time.sleep(2)
        
        # Устанавливаем вебхук
        response = requests.post(
            f"{TELEGRAM_API_URL}/setWebhook",
            json={'url': webhook_url},
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"✅ Webhook set successfully: {response.json()}")
        else:
            logger.error(f"❌ Failed to set webhook: {response.status_code} - {response.text}")
        
        # Запускаем самопинг
        self_ping()
        
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")
else:
    logger.error("❌ BOT_TOKEN not configured!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

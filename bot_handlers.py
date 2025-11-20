import logging
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import DISTRICTS_INFO, ORG_INFO, DOCUMENTS_LIST, FAQ_TEXT, is_admin, ADMINS
from database import save_user_session, log_user_action, init_db

logger = logging.getLogger(__name__)

# Глобальная переменная для хранения экземпляра бота
current_bot = None

def setup_bot_handlers(bot):
    """Настройка всех обработчиков для pyTelegramBotAPI"""
    global current_bot
    current_bot = bot
    
    # Инициализация БД
    init_db()
    
    # Команда /start
    @bot.message_handler(commands=['start'])
    def start_command(message):
        user = message.from_user
        logger.info(f"👤 User {user.id} started the bot")
        save_user_session(user.id, user.username, user.first_name, user.last_name)
        log_user_action(user.id, 'start')
        
        # Проверяем, является ли пользователь администратором
        if is_admin(user.id):
            show_admin_menu(bot, message)
            return
        
        keyboard = [
            [InlineKeyboardButton("🏃 Выбрать район", callback_data='main_districts')],
            [InlineKeyboardButton("💳 Реквизиты оплаты", callback_data='main_payment')],
            [InlineKeyboardButton("📋 Список документов", callback_data='main_documents')],
            [InlineKeyboardButton("❓ Частые вопросы", callback_data='main_faq')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
🤺 Добро пожаловать в <b>Тольяттинскую федерацию фехтования</b>!

Здесь вы можете:
• Выбрать удобный район для тренировок
• Узнать реквизиты для оплаты
• Получить список необходимых документов
• Найти ответы на частые вопросы

Выберите нужный раздел:
        """
        
        bot.send_message(message.chat.id, welcome_text, reply_markup=reply_markup, parse_mode='HTML')

    # Обработчики callback-запросов
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call):
        logger.info(f"🔘 Callback received: {call.data}")
        
        if call.data.startswith('main_'):
            handle_main_menu(call)
        elif call.data.startswith('district_'):
            handle_district_selection(call)
        elif call.data.startswith('admin_'):
            handle_admin_actions(call)
        elif call.data.startswith('back_'):
            handle_back(call)

    def handle_main_menu(call):
        action = call.data.replace('main_', '')
        
        if action == 'districts':
            show_districts_menu(bot, call)
        elif action == 'payment':
            send_payment_info_callback(bot, call)
        elif action == 'documents':
            send_documents_info_callback(bot, call)
        elif action == 'faq':
            send_faq_info_callback(bot, call)

    def handle_district_selection(call):
        district_key = call.data.replace('district_', '')
        district_info = DISTRICTS_INFO.get(district_key)
        
        if not district_info:
            bot.edit_message_text("Район не найден", call.message.chat.id, call.message.message_id)
            return
        
        message = format_district_info(district_info)
        keyboard = [
            [InlineKeyboardButton("💳 Реквизиты оплаты", callback_data='main_payment')],
            [InlineKeyboardButton("📋 Документы", callback_data='main_documents')],
            [InlineKeyboardButton("◀️ Выбрать другой район", callback_data='main_districts')],
            [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.edit_message_text(message, call.message.chat.id, call.message.message_id, reply_markup=reply_markup, parse_mode='HTML')

    def handle_admin_actions(call):
        user = call.from_user
        
        if not is_admin(user.id):
            bot.answer_callback_query(call.id, "⛔ У вас нет прав доступа.")
            return
        
        action = call.data.replace('admin_', '')
        
        if action == 'stats':
            show_stats_menu(bot, call)
        elif action == 'back':
            show_admin_menu_from_callback(bot, call)

    def handle_back(call):
        action = call.data.replace('back_', '')
        
        if action == 'to_main':
            start_command_callback(bot, call)

    # Вспомогательные функции
    def show_admin_menu(bot, message):
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
            [InlineKeyboardButton("📢 Рассылка", callback_data='admin_broadcast')],
            [InlineKeyboardButton("👥 Поиск пользователя", callback_data='admin_search')],
            [InlineKeyboardButton("🏠 Пользовательское меню", callback_data='back_to_main')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_text = f"""
🛠 <b>Панель администратора</b>

👑 Администраторов: {len(ADMINS)}
Выберите действие:
        """
        
        bot.send_message(message.chat.id, admin_text, reply_markup=reply_markup, parse_mode='HTML')

    def show_districts_menu(bot, call):
        keyboard = [
            [InlineKeyboardButton("Центральный район", callback_data='district_central')],
            [InlineKeyboardButton("Автозаводский район", callback_data='district_avtozavodsky')],
            [InlineKeyboardButton("Комсомольский район", callback_data='district_komso')],
            [InlineKeyboardButton("Жигулёвск", callback_data='district_zhig')],
            [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🏃 <b>Выберите район:</b>\n\nПосле выбора района вы получите:\n• Адрес и расписание\n• Ссылку на чат родителей\n• Всю необходимую информацию"
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=reply_markup, parse_mode='HTML')

    def send_payment_info_callback(bot, call):
        text = format_payment_info()
        keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=reply_markup, parse_mode='HTML')

    def send_documents_info_callback(bot, call):
        keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        bot.edit_message_text(DOCUMENTS_LIST, call.message.chat.id, call.message.message_id, reply_markup=reply_markup, parse_mode='HTML')

    def send_faq_info_callback(bot, call):
        keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        bot.edit_message_text(FAQ_TEXT, call.message.chat.id, call.message.message_id, reply_markup=reply_markup, parse_mode='HTML')

    def show_stats_menu(bot, call):
        from database import get_statistics
        stats = get_statistics()
        
        stats_text = f"""
📊 <b>Статистика бота</b>

👥 <b>Пользователи:</b>
• Всего: {stats['total_users']}
• Активных: {stats['active_users']}
        """
        
        keyboard = [[InlineKeyboardButton("◀️ Назад в админку", callback_data='admin_back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, reply_markup=reply_markup, parse_mode='HTML')

    def show_admin_menu_from_callback(bot, call):
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
            [InlineKeyboardButton("📢 Рассылка", callback_data='admin_broadcast')],
            [InlineKeyboardButton("👥 Поиск пользователя", callback_data='admin_search')],
            [InlineKeyboardButton("🏠 Пользовательское меню", callback_data='back_to_main')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_text = f"""
🛠 <b>Панель администратора</b>

👑 Администраторов: {len(ADMINS)}
Выберите действие:
        """
        
        bot.edit_message_text(admin_text, call.message.chat.id, call.message.message_id, reply_markup=reply_markup, parse_mode='HTML')

    def start_command_callback(bot, call):
        user = call.from_user
        
        if is_admin(user.id):
            keyboard = [
                [InlineKeyboardButton("🏃 Выбрать район", callback_data='main_districts')],
                [InlineKeyboardButton("💳 Реквизиты оплаты", callback_data='main_payment')],
                [InlineKeyboardButton("📋 Список документов", callback_data='main_documents')],
                [InlineKeyboardButton("❓ Частые вопросы", callback_data='main_faq')],
                [InlineKeyboardButton("🛠 Админ-панель", callback_data='admin_back')]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("🏃 Выбрать район", callback_data='main_districts')],
                [InlineKeyboardButton("💳 Реквизиты оплаты", callback_data='main_payment')],
                [InlineKeyboardButton("📋 Список документов", callback_data='main_documents')],
                [InlineKeyboardButton("❓ Частые вопросы", callback_data='main_faq')]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = "🤺 Добро пожаловать в <b>Тольяттинскую федерацию фехтования</b>!\n\nВыберите нужный раздел:"
        
        bot.edit_message_text(welcome_text, call.message.chat.id, call.message.message_id, reply_markup=reply_markup, parse_mode='HTML')

    logger.info("✅ All bot handlers registered successfully")

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

import logging
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import DISTRICTS_INFO, ORG_INFO, DOCUMENTS_LIST, FAQ_TEXT, is_admin, ADMINS
from database import save_user_session, log_user_action, init_db, get_statistics

logger = logging.getLogger(__name__)

def setup_bot_handlers(bot):
    """Настройка всех обработчиков для pyTelegramBotAPI"""
    
    # Инициализация БД
    try:
        init_db()
        logger.info("✅ База данных инициализирована в обработчиках")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД в обработчиках: {e}")
    
    # Добавим диагностический обработчик для всех сообщений
    @bot.message_handler(func=lambda message: True)
    def debug_all_messages(message):
        logger.info(f"🔍 Received message: {message.text} from user: {message.from_user.id}")
        # Не отвечаем, просто логируем
    
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
        
        try:
            bot.send_message(message.chat.id, welcome_text, reply_markup=reply_markup, parse_mode='HTML')
            logger.info(f"✅ Start message sent to user {user.id}")
        except Exception as e:
            logger.error(f"❌ Failed to send start message: {e}")

    # Команда /help
    @bot.message_handler(commands=['help'])
    def help_command(message):
        user = message.from_user
        
        help_text = """
🤖 <b>Доступные команды:</b>

/start - Главное меню
/help - Эта справка
/payment - Реквизиты для оплаты
/documents - Список документов
/faq - Частые вопросы
        """
        
        if is_admin(user.id):
            help_text += """
            
🛠 <b>Команды администратора:</b>

/admin - Панель администратора
/stats - Статистика бота
            """
        
        help_text += "\nИли просто используйте кнопки меню!"
        
        bot.send_message(message.chat.id, help_text, parse_mode='HTML')

    @bot.message_handler(commands=['payment'])
    def payment_command(message):
        send_payment_info(bot, message)

    @bot.message_handler(commands=['documents'])
    def documents_command(message):
        send_documents_info(bot, message)

    @bot.message_handler(commands=['faq'])
    def faq_command(message):
        send_faq_info(bot, message)

    @bot.message_handler(commands=['admin'])
    def admin_command(message):
        user = message.from_user
        
        if not is_admin(user.id):
            bot.send_message(message.chat.id, "⛔ У вас нет прав доступа к админ-панели.")
            return
        
        show_admin_menu(bot, message)

    @bot.message_handler(commands=['stats'])
    def stats_command(message):
        user = message.from_user
        
        if not is_admin(user.id):
            bot.send_message(message.chat.id, "⛔ У вас нет прав доступа к этой команде.")
            return
        
        stats = get_statistics()
        
        stats_text = f"""
📊 <b>Статистика бота</b>

👥 <b>Пользователи:</b>
• Всего: {stats['total_users']}
• Активных: {stats['active_users']}
        """
        
        for action_type, count in stats['actions_count'].items():
            stats_text += f"• {action_type}: {count}\n"
        
        bot.send_message(message.chat.id, stats_text, parse_mode='HTML')

    # Обработчики callback-запросов
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call):
        logger.info(f"🔘 Callback received: {call.data}")
        
        if call.data.startswith('main_'):
            handle_main_menu(bot, call)
        elif call.data.startswith('district_'):
            handle_district_selection(bot, call)
        elif call.data.startswith('base_'):
            handle_base_selection(bot, call)
        elif call.data.startswith('admin_'):
            handle_admin_actions(bot, call)
        elif call.data.startswith('back_'):
            handle_back(bot, call)

    logger.info("✅ All bot handlers registered successfully")

# Остальные функции остаются без изменений...
# [ВСТАВЬТЕ ЗДЕСЬ ВСЕ ОСТАЛЬНЫЕ ФУНКЦИИ ИЗ ВАШЕГО ИСХОДНОГО bot_handlers.py]

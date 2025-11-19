import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackQueryHandler,
    Application
)
from config import DISTRICTS_INFO, ORG_INFO, DOCUMENTS_LIST, FAQ_TEXT, is_admin, ADMINS
from database import save_user_session, log_user_action, init_db, get_statistics, get_user_info, log_admin_action, broadcast_message

logger = logging.getLogger(__name__)

def setup_handlers(application: Application):
    """Настройка всех обработчиков для версии 20.x"""
    
    # Команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("payment", payment_command))
    application.add_handler(CommandHandler("documents", documents_command))
    application.add_handler(CommandHandler("faq", faq_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Callback запросы
    application.add_handler(CallbackQueryHandler(handle_district_selection, pattern='^district_'))
    application.add_handler(CallbackQueryHandler(handle_base_selection, pattern='^base_'))
    application.add_handler(CallbackQueryHandler(handle_main_menu, pattern='^main_'))
    application.add_handler(CallbackQueryHandler(handle_back, pattern='^back_'))
    application.add_handler(CallbackQueryHandler(handle_admin_actions, pattern='^admin_'))
    
    # Обработчики текстовых сообщений (для рассылки)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Инициализация БД
    init_db()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    save_user_session(user.id, user.username, user.first_name, user.last_name)
    log_user_action(user.id, 'start')
    
    # Проверяем, является ли пользователь администратором
    if is_admin(user.id):
        await show_admin_menu(update, context)
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
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /admin"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ У вас нет прав доступа к админ-панели.")
        return
    
    await show_admin_menu(update, context)

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню администратора"""
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
    
    if update.callback_query:
        await update.callback_query.edit_message_text(admin_text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode='HTML')

# Остальные функции остаются аналогичными, но с async/await
# Для экономии места покажу шаблон, остальные функции адаптируйте аналогично

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    user = update.effective_user
    
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
/broadcast - Рассылка сообщений
        """
    
    help_text += "\nИли просто используйте кнопки меню!"
    
    await update.message.reply_text(help_text, parse_mode='HTML')

async def payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /payment"""
    await send_payment_info(update, context)

async def send_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить информацию об оплате"""
    message = format_payment_info()
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def documents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /documents"""
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(DOCUMENTS_LIST, reply_markup=reply_markup, parse_mode='HTML')

async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /faq"""
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(FAQ_TEXT, reply_markup=reply_markup, parse_mode='HTML')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stats"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ У вас нет прав доступа к этой команде.")
        return
    
    stats = get_statistics()
    
    stats_text = f"""
📊 <b>Статистика бота</b>

👥 <b>Пользователи:</b>
• Всего: {stats['total_users']}
• Активных: {stats['active_users']}
"""
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в админку", callback_data='admin_back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode='HTML')

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /broadcast"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ У вас нет прав доступа к этой команде.")
        return
    
    if not context.args:
        keyboard = [
            [InlineKeyboardButton("📢 Всем пользователям", callback_data='admin_broadcast_all')],
            [InlineKeyboardButton("👥 Только пользователям (без админов)", callback_data='admin_broadcast_users')],
            [InlineKeyboardButton("◀️ Назад", callback_data='admin_back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📢 <b>Рассылка сообщений</b>\n\nВыберите тип рассылки:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user = update.effective_user
    message_text = update.message.text
    
    # Проверяем, ожидается ли сообщение для рассылки
    if is_admin(user.id) and context.user_data.get('awaiting_broadcast'):
        # Здесь будет логика рассылки
        context.user_data['awaiting_broadcast'] = False
        await update.message.reply_text("📢 Режим рассылки активирован (заглушка)")
        return
    
    log_user_action(user.id, 'message')
    await update.message.reply_text(
        "Используйте команды или кнопки меню для навигации. Если вы заблудились, введите /start"
    )

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик действий администратора"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if not is_admin(user.id):
        await query.edit_message_text("⛔ У вас нет прав доступа.")
        return
    
    action = query.data.replace('admin_', '')
    
    if action == 'stats':
        await show_stats_menu(query)
    elif action == 'broadcast':
        await show_broadcast_menu(query)
    elif action == 'search':
        await show_search_menu(query)
    elif action == 'back':
        await show_admin_menu_from_callback(query)

async def show_stats_menu(query):
    """Показать меню статистики"""
    stats = get_statistics()
    
    stats_text = f"""
📊 <b>Статистика бота</b>

👥 <b>Пользователи:</b>
• Всего: {stats['total_users']}
• Активных: {stats['active_users']}
"""
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в админку", callback_data='admin_back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='HTML')

async def show_broadcast_menu(query):
    """Показать меню рассылки"""
    keyboard = [
        [InlineKeyboardButton("📢 Всем пользователям", callback_data='admin_broadcast_all')],
        [InlineKeyboardButton("👥 Только пользователям (без админов)", callback_data='admin_broadcast_users')],
        [InlineKeyboardButton("◀️ Назад", callback_data='admin_back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📢 <b>Рассылка сообщений</b>\n\nВыберите тип рассылки:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def show_search_menu(query):
    """Показать меню поиска пользователя"""
    await query.edit_message_text(
        "👥 <b>Поиск пользователя</b>\n\n"
        "Функция в разработке...",
        parse_mode='HTML'
    )

async def show_admin_menu_from_callback(query):
    """Показать меню администратора из callback"""
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
    
    await query.edit_message_text(admin_text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace('main_', '')
    
    if action == 'districts':
        await show_districts_menu(query)
    elif action == 'payment':
        await send_payment_info_callback(query)
    elif action == 'documents':
        await send_documents_info_callback(query)
    elif action == 'faq':
        await send_faq_info_callback(query)

async def show_districts_menu(query):
    """Показать меню выбора района"""
    keyboard = [
        [InlineKeyboardButton("Центральный район", callback_data='district_central')],
        [InlineKeyboardButton("Автозаводский район", callback_data='district_avtozavodsky')],
        [InlineKeyboardButton("Комсомольский район", callback_data='district_komso')],
        [InlineKeyboardButton("Жигулёвск", callback_data='district_zhig')],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏃 <b>Выберите район:</b>\n\n"
        "После выбора района вы получите:\n"
        "• Адрес и расписание\n"
        "• Ссылку на чат родителей\n"
        "• Всю необходимую информацию",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_district_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора района"""
    query = update.callback_query
    await query.answer()
    
    district_key = query.data.replace('district_', '')
    district_info = DISTRICTS_INFO.get(district_key)
    
    if not district_info:
        await query.edit_message_text("Район не найден")
        return
    
    # Для Автозаводского района показываем выбор базы
    if district_key == 'avtozavodsky':
        await show_bases_menu(query, district_info)
        return
    
    # Для других районов показываем информацию сразу
    message = format_district_info(district_info)
    keyboard = [
        [InlineKeyboardButton("💳 Реквизиты оплаты", callback_data='main_payment')],
        [InlineKeyboardButton("📋 Документы", callback_data='main_documents')],
        [InlineKeyboardButton("◀️ Выбрать другой район", callback_data='main_districts')],
        [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def show_bases_menu(query, district_info):
    """Показать меню выбора базы для Автозаводского района"""
    keyboard = []
    
    for base_key, base_info in district_info['bases'].items():
        keyboard.append([InlineKeyboardButton(base_info['name'], callback_data=f'base_{base_key}')])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад к районам", callback_data='main_districts')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏢 <b>Автозаводский район</b>\n\nВыберите удобную вам базу:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_base_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора базы"""
    query = update.callback_query
    await query.answer()
    
    base_key = query.data.replace('base_', '')
    district_info = DISTRICTS_INFO['avtozavodsky']
    base_info = district_info['bases'].get(base_key)
    
    if not base_info:
        await query.edit_message_text("База не найдена")
        return
    
    message = format_base_info(district_info, base_info)
    keyboard = [
        [InlineKeyboardButton("💳 Реквизиты оплаты", callback_data='main_payment')],
        [InlineKeyboardButton("📋 Документы", callback_data='main_documents')],
        [InlineKeyboardButton("◀️ Выбрать другую базу", callback_data='district_avtozavodsky')],
        [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки Назад"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace('back_', '')
    
    if action == 'to_main':
        await start_command_callback(query)

async def start_command_callback(query):
    """Главное меню для callback"""
    user = query.from_user
    
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
    
    await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

async def send_payment_info_callback(query):
    """Отправить информацию об оплате (callback)"""
    message = format_payment_info()
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def send_documents_info_callback(query):
    """Отправить список документов (callback)"""
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(DOCUMENTS_LIST, reply_markup=reply_markup, parse_mode='HTML')

async def send_faq_info_callback(query):
    """Отправить FAQ (callback)"""
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(FAQ_TEXT, reply_markup=reply_markup, parse_mode='HTML')

# Вспомогательные функции форматирования (без изменений)
def format_district_info(district_info):
    """Форматирование информации о районе"""
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
    """Форматирование информации о базе"""
    return f"""
<b>{district_info['name']} - {base_info['name']}</b>

📍 <b>Адрес:</b> {base_info['address']}

📅 <b>Расписание:</b>
{base_info['schedule']}

💬 <b>Чат для родителей:</b> {district_info['chat_link']}

💰 <b>Стоимость:</b> {district_info['price']}

👕 <b>С собой на тренировку:</b> сменные кроссовки для зала, белые носки, спортивная форма, бутылочка с водой

⚠️ <b>Важно:</b> пока не нужно платить и приносить документы! Все в процессе!
    """

def format_payment_info():
    """Форматирование информации об оплате"""
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

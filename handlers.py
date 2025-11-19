import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackContext, 
    CommandHandler, 
    MessageHandler, 
    Filters, 
    CallbackQueryHandler,
    Updater
)
from config import DISTRICTS_INFO, ORG_INFO, DOCUMENTS_LIST, FAQ_TEXT, is_admin, ADMINS
from database import save_user_session, log_user_action, init_db, get_statistics, get_user_info, log_admin_action, broadcast_message

logger = logging.getLogger(__name__)

def setup_handlers(updater: Updater):
    """Настройка всех обработчиков для версии 13.x"""
    dp = updater.dispatcher
    
    # Команды
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("payment", payment_command))
    dp.add_handler(CommandHandler("documents", documents_command))
    dp.add_handler(CommandHandler("faq", faq_command))
    dp.add_handler(CommandHandler("stats", stats_command))
    dp.add_handler(CommandHandler("admin", admin_command))
    dp.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Callback запросы
    dp.add_handler(CallbackQueryHandler(handle_district_selection, pattern='^district_'))
    dp.add_handler(CallbackQueryHandler(handle_base_selection, pattern='^base_'))
    dp.add_handler(CallbackQueryHandler(handle_main_menu, pattern='^main_'))
    dp.add_handler(CallbackQueryHandler(handle_back, pattern='^back_'))
    dp.add_handler(CallbackQueryHandler(handle_admin_actions, pattern='^admin_'))
    
    # Обработчики текстовых сообщений (для рассылки)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Инициализация БД
    init_db()

def start_command(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    user = update.effective_user
    save_user_session(user.id, user.username, user.first_name, user.last_name)
    log_user_action(user.id, 'start')
    
    # Проверяем, является ли пользователь администратором
    if is_admin(user.id):
        show_admin_menu(update, context)
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
    
    update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

def admin_command(update: Update, context: CallbackContext):
    """Обработчик команды /admin"""
    user = update.effective_user
    
    if not is_admin(user.id):
        update.message.reply_text("⛔ У вас нет прав доступа к админ-панели.")
        return
    
    show_admin_menu(update, context)

def show_admin_menu(update: Update, context: CallbackContext):
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
        update.callback_query.edit_message_text(admin_text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode='HTML')

def stats_command(update: Update, context: CallbackContext):
    """Обработчик команды /stats"""
    user = update.effective_user
    
    if not is_admin(user.id):
        update.message.reply_text("⛔ У вас нет прав доступа к этой команде.")
        return
    
    stats = get_statistics()
    
    stats_text = f"""
📊 <b>Статистика бота</b>

👥 <b>Пользователи:</b>
• Всего: {stats['total_users']}
• Активных: {stats['active_users']}

📈 <b>Действия:</b>
"""
    
    for action_type, count in stats['actions_count'].items():
        stats_text += f"• {action_type}: {count}\n"
    
    stats_text += f"\n🕒 <b>Последние действия:</b>\n"
    for action_type, timestamp in stats['recent_actions']:
        stats_text += f"• {action_type} - {timestamp}\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в админку", callback_data='admin_back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode='HTML')

def broadcast_command(update: Update, context: CallbackContext):
    """Обработчик команды /broadcast"""
    user = update.effective_user
    
    if not is_admin(user.id):
        update.message.reply_text("⛔ У вас нет прав доступа к этой команде.")
        return
    
    if not context.args:
        # Показываем меню рассылки
        keyboard = [
            [InlineKeyboardButton("📢 Всем пользователям", callback_data='admin_broadcast_all')],
            [InlineKeyboardButton("👥 Только пользователям (без админов)", callback_data='admin_broadcast_users')],
            [InlineKeyboardButton("◀️ Назад", callback_data='admin_back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "📢 <b>Рассылка сообщений</b>\n\n"
            "Выберите тип рассылки:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return
    
    # Если текст передан сразу с командой
    message_text = ' '.join(context.args)
    execute_broadcast(update, context, message_text, 'all')

def handle_admin_actions(update: Update, context: CallbackContext):
    """Обработчик действий администратора"""
    query = update.callback_query
    query.answer()
    
    user = query.from_user
    
    if not is_admin(user.id):
        query.edit_message_text("⛔ У вас нет прав доступа.")
        return
    
    action = query.data.replace('admin_', '')
    
    if action == 'stats':
        show_stats_menu(query)
    elif action == 'broadcast':
        show_broadcast_menu(query)
    elif action == 'search':
        show_search_menu(query)
    elif action == 'back':
        show_admin_menu_from_callback(query)
    elif action == 'broadcast_all':
        context.user_data['broadcast_type'] = 'all'
        context.user_data['awaiting_broadcast'] = True
        query.edit_message_text(
            "📢 <b>Рассылка всем пользователям</b>\n\n"
            "Введите сообщение для рассылки:",
            parse_mode='HTML'
        )
    elif action == 'broadcast_users':
        context.user_data['broadcast_type'] = 'users'
        context.user_data['awaiting_broadcast'] = True
        query.edit_message_text(
            "📢 <b>Рассылка только пользователям</b>\n\n"
            "Введите сообщение для рассылки:",
            parse_mode='HTML'
        )

def handle_message(update: Update, context: CallbackContext):
    """Обработчик текстовых сообщений"""
    user = update.effective_user
    message_text = update.message.text
    
    # Проверяем, ожидается ли сообщение для рассылки
    if is_admin(user.id) and context.user_data.get('awaiting_broadcast'):
        broadcast_type = context.user_data.get('broadcast_type', 'all')
        execute_broadcast(update, context, message_text, broadcast_type)
        context.user_data['awaiting_broadcast'] = False
        return
    
    # Обычная обработка сообщений
    log_user_action(user.id, 'message')
    update.message.reply_text(
        "Используйте команды или кнопки меню для навигации. "
        "Если вы заблудились, введите /start"
    )

def execute_broadcast(update: Update, context: CallbackContext, message_text, broadcast_type):
    """Выполняет рассылку сообщения"""
    user = update.effective_user
    
    # Получаем список пользователей для рассылки
    if broadcast_type == 'all':
        users = broadcast_message(message_text, exclude_admins=False)
        target = "всем пользователям"
    else:
        users = broadcast_message(message_text, exclude_admins=True)
        target = "только пользователям (без админов)"
    
    total_users = len(users)
    successful = 0
    failed = 0
    
    # Отправляем сообщение о начале рассылки
    status_message = update.message.reply_text(
        f"📢 <b>Начинаю рассылку</b>\n\n"
        f"Целевая аудитория: {target}\n"
        f"Количество пользователей: {total_users}\n"
        f"Статус: 0/{total_users}",
        parse_mode='HTML'
    )
    
    # Выполняем рассылку
    for i, user_id in enumerate(users):
        try:
            context.bot.send_message(
                chat_id=user_id,
                text=f"📢 <b>Сообщение от администрации:</b>\n\n{message_text}",
                parse_mode='HTML'
            )
            successful += 1
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
            failed += 1
        
        # Обновляем статус каждые 10 отправок
        if i % 10 == 0 or i == total_users - 1:
            try:
                context.bot.edit_message_text(
                    chat_id=status_message.chat_id,
                    message_id=status_message.message_id,
                    text=f"📢 <b>Рассылка в процессе</b>\n\n"
                         f"Целевая аудитория: {target}\n"
                         f"Количество пользователей: {total_users}\n"
                         f"Статус: {i+1}/{total_users}\n"
                         f"✅ Успешно: {successful}\n"
                         f"❌ Ошибок: {failed}",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Ошибка обновления статуса: {e}")
    
    # Логируем действие администратора
    log_admin_action(
        user.id,
        'broadcast',
        details=f"Тип: {broadcast_type}, Получателей: {total_users}, Успешно: {successful}, Ошибок: {failed}"
    )
    
    # Финальное сообщение
    try:
        context.bot.edit_message_text(
            chat_id=status_message.chat_id,
            message_id=status_message.message_id,
            text=f"✅ <b>Рассылка завершена</b>\n\n"
                 f"Целевая аудитория: {target}\n"
                 f"Всего пользователей: {total_users}\n"
                 f"✅ Успешно отправлено: {successful}\n"
                 f"❌ Ошибок отправки: {failed}",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Ошибка финального обновления статуса: {e}")

def show_stats_menu(query):
    """Показать меню статистики"""
    stats = get_statistics()
    
    stats_text = f"""
📊 <b>Статистика бота</b>

👥 <b>Пользователи:</b>
• Всего: {stats['total_users']}
• Активных: {stats['active_users']}

📈 <b>Действия:</b>
"""
    
    for action_type, count in stats['actions_count'].items():
        stats_text += f"• {action_type}: {count}\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в админку", callback_data='admin_back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='HTML')

def show_broadcast_menu(query):
    """Показать меню рассылки"""
    keyboard = [
        [InlineKeyboardButton("📢 Всем пользователям", callback_data='admin_broadcast_all')],
        [InlineKeyboardButton("👥 Только пользователям (без админов)", callback_data='admin_broadcast_users')],
        [InlineKeyboardButton("◀️ Назад", callback_data='admin_back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Выберите тип рассылки:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

def show_search_menu(query):
    """Показать меню поиска пользователя"""
    query.edit_message_text(
        "👥 <b>Поиск пользователя</b>\n\n"
        "Для поиска пользователя используйте команду:\n"
        "<code>/user USER_ID</code>\n\n"
        "Чтобы получить ID пользователя, перешлите его сообщение боту @userinfobot",
        parse_mode='HTML'
    )

def show_admin_menu_from_callback(query):
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
    
    query.edit_message_text(admin_text, reply_markup=reply_markup, parse_mode='HTML')

# Команды для обычных пользователей
def help_command(update: Update, context: CallbackContext):
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
    
    # Добавляем админские команды для администраторов
    if is_admin(user.id):
        help_text += """
        
🛠 <b>Команды администратора:</b>

/admin - Панель администратора
/stats - Статистика бота
/broadcast - Рассылка сообщений
        """
    
    help_text += "\nИли просто используйте кнопки меню!"
    
    update.message.reply_text(help_text, parse_mode='HTML')

def payment_command(update: Update, context: CallbackContext):
    """Обработчик команды /payment"""
    send_payment_info(update, context)

def documents_command(update: Update, context: CallbackContext):
    """Обработчик команды /documents"""
    send_documents_info(update, context)

def faq_command(update: Update, context: CallbackContext):
    """Обработчик команды /faq"""
    send_faq_info(update, context)

def send_payment_info(update: Update, context: CallbackContext):
    """Отправить информацию об оплате (команда)"""
    message = format_payment_info()
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

def send_payment_info_callback(query):
    """Отправить информацию об оплате (callback)"""
    message = format_payment_info()
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

def send_documents_info(update: Update, context: CallbackContext):
    """Отправить список документов (команда)"""
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(DOCUMENTS_LIST, reply_markup=reply_markup, parse_mode='HTML')

def send_documents_info_callback(query):
    """Отправить список документов (callback)"""
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(DOCUMENTS_LIST, reply_markup=reply_markup, parse_mode='HTML')

def send_faq_info(update: Update, context: CallbackContext):
    """Отправить FAQ (команда)"""
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(FAQ_TEXT, reply_markup=reply_markup, parse_mode='HTML')

def send_faq_info_callback(query):
    """Отправить FAQ (callback)"""
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(FAQ_TEXT, reply_markup=reply_markup, parse_mode='HTML')

# Обработчики основного меню
def handle_main_menu(update: Update, context: CallbackContext):
    """Обработчик главного меню"""
    query = update.callback_query
    query.answer()
    
    action = query.data.replace('main_', '')
    
    if action == 'districts':
        show_districts_menu(query)
    elif action == 'payment':
        send_payment_info_callback(query)
    elif action == 'documents':
        send_documents_info_callback(query)
    elif action == 'faq':
        send_faq_info_callback(query)

def show_districts_menu(query):
    """Показать меню выбора района"""
    keyboard = [
        [InlineKeyboardButton("Центральный район", callback_data='district_central')],
        [InlineKeyboardButton("Автозаводский район", callback_data='district_avtozavodsky')],
        [InlineKeyboardButton("Комсомольский район", callback_data='district_komso')],
        [InlineKeyboardButton("Жигулёвск", callback_data='district_zhig')],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "🏃 <b>Выберите район:</b>\n\n"
        "После выбора района вы получите:\n"
        "• Адрес и расписание\n"
        "• Ссылку на чат родителей\n"
        "• Всю необходимую информацию",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

def handle_district_selection(update: Update, context: CallbackContext):
    """Обработчик выбора района"""
    query = update.callback_query
    query.answer()
    
    district_key = query.data.replace('district_', '')
    district_info = DISTRICTS_INFO.get(district_key)
    
    if not district_info:
        query.edit_message_text("Район не найден")
        return
    
    # Для Автозаводского района показываем выбор базы
    if district_key == 'avtozavodsky':
        show_bases_menu(query, district_info)
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
    query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

def show_bases_menu(query, district_info):
    """Показать меню выбора базы для Автозаводского района"""
    keyboard = []
    
    for base_key, base_info in district_info['bases'].items():
        keyboard.append([InlineKeyboardButton(base_info['name'], callback_data=f'base_{base_key}')])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад к районам", callback_data='main_districts')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "🏢 <b>Автозаводский район</b>\n\n"
        "Выберите удобную вам базу:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

def handle_base_selection(update: Update, context: CallbackContext):
    """Обработчик выбора базы"""
    query = update.callback_query
    query.answer()
    
    base_key = query.data.replace('base_', '')
    district_info = DISTRICTS_INFO['avtozavodsky']
    base_info = district_info['bases'].get(base_key)
    
    if not base_info:
        query.edit_message_text("База не найдена")
        return
    
    message = format_base_info(district_info, base_info)
    keyboard = [
        [InlineKeyboardButton("💳 Реквизиты оплаты", callback_data='main_payment')],
        [InlineKeyboardButton("📋 Документы", callback_data='main_documents')],
        [InlineKeyboardButton("◀️ Выбрать другую базу", callback_data='district_avtozavodsky')],
        [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

def handle_back(update: Update, context: CallbackContext):
    """Обработчик кнопки Назад"""
    query = update.callback_query
    query.answer()
    
    action = query.data.replace('back_', '')
    
    if action == 'to_main':
        start_command_callback(query)

def start_command_callback(query):
    """Главное меню для callback"""
    user = query.from_user
    
    # Проверяем, является ли пользователь администратором
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
    
    welcome_text = f"""
🤺 Добро пожаловать в <b>Тольяттинскую федерации фехтования</b>!

Выберите нужный раздел:
    """
    
    query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

# Вспомогательные функции форматирования
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

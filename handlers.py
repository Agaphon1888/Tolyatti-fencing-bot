from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext
import logging
from config import DISTRICTS_INFO, ORG_INFO, DOCUMENTS_LIST, FAQ_TEXT, is_admin, ADMINS
from database import save_user_session, log_user_action, init_db, get_statistics, get_user_info, log_admin_action, broadcast_message

logger = logging.getLogger(__name__)

def setup_handlers(application):
    """Настройка всех обработчиков"""
    
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

📈 <b>Действия:</b>
"""
    
    for action_type, count in stats['actions_count'].items():
        stats_text += f"• {action_type}: {count}\n"
    
    stats_text += f"\n🕒 <b>Последние действия:</b>\n"
    for action_type, timestamp in stats['recent_actions']:
        stats_text += f"• {action_type} - {timestamp}\n"
    
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
        # Показываем меню рассылки
        keyboard = [
            [InlineKeyboardButton("📢 Всем пользователям", callback_data='admin_broadcast_all')],
            [InlineKeyboardButton("👥 Только пользователям (без админов)", callback_data='admin_broadcast_users')],
            [InlineKeyboardButton("◀️ Назад", callback_data='admin_back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📢 <b>Рассылка сообщений</b>\n\n"
            "Выберите тип рассылки:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return
    
    # Если текст передан сразу с командой
    message_text = ' '.join(context.args)
    await execute_broadcast(update, context, message_text, 'all')

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
    elif action == 'broadcast_all':
        context.user_data['broadcast_type'] = 'all'
        await query.edit_message_text(
            "📢 <b>Рассылка всем пользователям</b>\n\n"
            "Введите сообщение для рассылки:",
            parse_mode='HTML'
        )
    elif action == 'broadcast_users':
        context.user_data['broadcast_type'] = 'users'
        await query.edit_message_text(
            "📢 <b>Рассылка только пользователям</b>\n\n"
            "Введите сообщение для рассылки:",
            parse_mode='HTML'
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user = update.effective_user
    message_text = update.message.text
    
    # Проверяем, ожидается ли сообщение для рассылки
    if is_admin(user.id) and context.user_data.get('awaiting_broadcast'):
        broadcast_type = context.user_data.get('broadcast_type', 'all')
        await execute_broadcast(update, context, message_text, broadcast_type)
        context.user_data['awaiting_broadcast'] = False
        return
    
    # Обычная обработка сообщений
    log_user_action(user.id, 'message')
    await update.message.reply_text(
        "Используйте команды или кнопки меню для навигации. "
        "Если вы заблудились, введите /start"
    )

async def execute_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text, broadcast_type):
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
    status_message = await update.message.reply_text(
        f"📢 <b>Начинаю рассылку</b>\n\n"
        f"Целевая аудитория: {target}\n"
        f"Количество пользователей: {total_users}\n"
        f"Статус: 0/{total_users}",
        parse_mode='HTML'
    )
    
    # Выполняем рассылку
    for i, user_id in enumerate(users):
        try:
            await context.bot.send_message(
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
            await status_message.edit_text(
                f"📢 <b>Рассылка в процессе</b>\n\n"
                f"Целевая аудитория: {target}\n"
                f"Количество пользователей: {total_users}\n"
                f"Статус: {i+1}/{total_users}\n"
                f"✅ Успешно: {successful}\n"
                f"❌ Ошибок: {failed}",
                parse_mode='HTML'
            )
    
    # Логируем действие администратора
    log_admin_action(
        user.id,
        'broadcast',
        details=f"Тип: {broadcast_type}, Получателей: {total_users}, Успешно: {successful}, Ошибок: {failed}"
    )
    
    # Финальное сообщение
    await status_message.edit_text(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"Целевая аудитория: {target}\n"
        f"Всего пользователей: {total_users}\n"
        f"✅ Успешно отправлено: {successful}\n"
        f"❌ Ошибок отправки: {failed}",
        parse_mode='HTML'
    )

async def show_stats_menu(query):
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
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Выберите тип рассылки:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def show_search_menu(query):
    """Показать меню поиска пользователя"""
    await query.edit_message_text(
        "👥 <b>Поиск пользователя</b>\n\n"
        "Для поиска пользователя используйте команду:\n"
        "<code>/user USER_ID</code>\n\n"
        "Чтобы получить ID пользователя, перешлите его сообщение боту @userinfobot",
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

# ... остальные функции из предыдущей версии остаются без изменений ...
# (start_command, help_command, payment_command, documents_command, faq_command,
# handle_district_selection, handle_base_selection, handle_main_menu, handle_back,
# format_district_info, format_base_info, format_payment_info)

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
    
    # Добавляем админские команды для администраторов
    if is_admin(user.id):
        help_text += """
        
🛠 <b>Команды администратора:</b>

/admin - Панель администратора
/stats - Статистика бота
/broadcast - Рассылка сообщений
        """
    
    help_text += "\nИли просто используйте кнопки меню!"
    
    await update.message.reply_text(help_text, parse_mode='HTML')

# Добавляем недостающие функции для совместимости
async def start_command_callback(query):
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
🤺 Добро пожаловать в <b>Тольяттинскую федерацию фехтования</b>!

Выберите нужный раздел:
    """
    
    await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

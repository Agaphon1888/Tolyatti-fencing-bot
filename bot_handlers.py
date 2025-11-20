def setup_bot_handlers(bot):
    """Настройка всех обработчиков для pyTelegramBotAPI"""
    
    # Инициализация БД
    init_db()
    
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

    # ... остальные обработчики остаются без изменений

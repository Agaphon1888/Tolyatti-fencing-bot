import os
import logging
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import asyncio
from threading import Thread
from config import BOT_TOKEN, PORT

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Глобальные переменные
bot_application = None
bot_instance = None

@app.route('/')
def home():
    return "🤺 Fencing Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Эндпоинт для вебхуков от Telegram"""
    try:
        if bot_application is None:
            return "Bot not initialized", 500
            
        # Получаем обновление от Telegram
        json_data = request.get_json()
        update = Update.de_json(json_data, bot_application.bot)
        
        # Создаем новое событие для обработки обновления
        asyncio.run_coroutine_threadsafe(
            bot_application.process_update(update), 
            bot_application._get_running_loop()
        )
        
        return "OK"
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

def setup_bot():
    """Настройка и запуск бота"""
    global bot_application, bot_instance
    
    try:
        logger.info("Initializing Telegram bot...")
        
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Настраиваем обработчики
        from handlers import setup_handlers
        setup_handlers(application)
        
        # Инициализируем приложение
        application.initialize()
        
        # Сохраняем ссылку
        bot_application = application
        bot_instance = application.bot
        
        # Устанавливаем вебхук
        webhook_url = os.getenv('RENDER_EXTERNAL_URL', '') or f"https://tolyatti-fencing-bot.onrender.com"
        if webhook_url:
            webhook_url = f"{webhook_url}/webhook"
            logger.info(f"Setting webhook to: {webhook_url}")
            
            # Устанавливаем вебхук синхронно
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot_instance.set_webhook(webhook_url))
            logger.info("Webhook set successfully!")
        
        logger.info("Bot setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Bot setup failed: {e}")

# Инициализируем бота при старте приложения
@app.before_first_request
def initialize_bot():
    """Инициализация бота при первом запросе"""
    thread = Thread(target=setup_bot, daemon=True)
    thread.start()

if __name__ == '__main__':
    # Для локальной разработки
    setup_bot()
    app.run(host='0.0.0.0', port=PORT, debug=False)

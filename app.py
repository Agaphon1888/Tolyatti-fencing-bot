import os
import logging
from flask import Flask, request
from telegram import Update
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
bot_initialized = False

@app.route('/')
def home():
    return "🤺 Fencing Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Эндпоинт для вебхуков от Telegram"""
    global bot_application
    try:
        if bot_application is None:
            logger.error("Bot application not initialized")
            return "Bot not initialized", 500
            
        # Получаем обновление от Telegram
        json_data = request.get_json()
        logger.info(f"Received webhook update: {json_data}")
        
        update = Update.de_json(json_data, bot_application.bot)
        
        # Обрабатываем обновление в отдельном потоке
        thread = Thread(target=process_update_async, args=(bot_application, update), daemon=True)
        thread.start()
        
        return "OK"
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

def process_update_async(application, update):
    """Обработка обновления в асинхронном режиме"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.process_update(update))
    except Exception as e:
        logger.error(f"Error processing update: {e}")

def setup_bot():
    """Настройка и запуск бота"""
    global bot_application, bot_initialized
    
    try:
        logger.info("🚀 Initializing Telegram bot...")
        
        if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            logger.error("❌ BOT_TOKEN not set or is default")
            return
        
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Настраиваем обработчики
        from handlers import setup_handlers
        setup_handlers(application)
        
        # Инициализируем приложение
        application.initialize()
        
        # Сохраняем ссылку
        bot_application = application
        
        # Устанавливаем вебхук
        webhook_url = os.getenv('RENDER_EXTERNAL_URL', '') or 'https://tolyatti-fencing-bot.onrender.com'
        if webhook_url:
            webhook_url = f"{webhook_url}/webhook"
            logger.info(f"🔗 Setting webhook to: {webhook_url}")
            
            # Устанавливаем вебхук
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(application.bot.set_webhook(webhook_url))
                logger.info("✅ Webhook set successfully!")
                
                # Проверяем вебхук
                webhook_info = loop.run_until_complete(application.bot.get_webhook_info())
                logger.info(f"📊 Webhook info: {webhook_info.url}, pending updates: {webhook_info.pending_update_count}")
                
            except Exception as e:
                logger.error(f"❌ Failed to set webhook: {e}")
        else:
            logger.warning("🌐 No webhook URL found, using polling fallback")
            # Запускаем polling в отдельном потоке
            def run_polling():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(application.run_polling())
                except Exception as e:
                    logger.error(f"Polling error: {e}")
            
            polling_thread = Thread(target=run_polling, daemon=True)
            polling_thread.start()
        
        bot_initialized = True
        logger.info("✅ Bot setup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Bot setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Инициализируем бота при импорте
logger.info("📦 Importing bot module, starting initialization...")
setup_bot()

if __name__ == '__main__':
    # Для локальной разработки
    app.run(host='0.0.0.0', port=PORT, debug=False)

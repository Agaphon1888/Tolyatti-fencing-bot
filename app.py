import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from config import BOT_TOKEN, PORT

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Глобальная переменная для бота
bot_application = None

@app.route('/')
def home():
    return "🤺 Fencing Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Обработка вебхуков от Telegram"""
    if bot_application is None:
        return "Bot not initialized", 500
    
    try:
        data = await request.get_json()
        update = Update.de_json(data, bot_application.bot)
        await bot_application.process_update(update)
        return "OK"
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

def setup_bot():
    """Настройка и запуск бота"""
    global bot_application
    
    try:
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Настраиваем обработчики
        from handlers import setup_handlers
        setup_handlers(application)
        
        # Сохраняем ссылку на application
        bot_application = application
        
        # Устанавливаем вебхук
        webhook_url = os.getenv('RENDER_EXTERNAL_URL') or f"https://{os.getenv('RENDER_SERVICE_NAME')}.onrender.com"
        
        if webhook_url and not webhook_url.startswith('https://'):
            webhook_url = f"https://{webhook_url}"
        
        if webhook_url:
            webhook_url = f"{webhook_url}/webhook"
            logger.info(f"Setting webhook to: {webhook_url}")
            application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=BOT_TOKEN,
                webhook_url=webhook_url
            )
        else:
            # Fallback to polling для локальной разработки
            logger.info("Using polling (no webhook URL found)")
            application.run_polling()
            
    except Exception as e:
        logger.error(f"Bot setup error: {e}")

if __name__ == '__main__':
    setup_bot()

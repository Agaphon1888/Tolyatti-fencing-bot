import os
import logging
from flask import Flask
import threading
from config import BOT_TOKEN, PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "🤺 Fencing Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/webhook', methods=['POST'])
def webhook():
    return "OK"

def run_bot():
    """Запуск бота в отдельном потоке"""
    try:
        logger.info("🚀 Starting Telegram bot...")
        from telegram.ext import Updater
        from handlers import setup_handlers
        
        updater = Updater(token=BOT_TOKEN, use_context=True)
        
        # Настраиваем обработчики
        setup_handlers(updater)
        
        # Запускаем polling
        updater.start_polling()
        logger.info("✅ Bot started successfully with polling!")
        
        # Блокируем поток
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Bot failed to start: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Запускаем бота только если токен установлен
if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE':
    logger.info("🚀 Starting bot thread...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
else:
    logger.error("❌ BOT_TOKEN not configured!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

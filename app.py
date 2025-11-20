import os
import logging
from flask import Flask
import threading
import time
import requests
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
        logger.info("🚀 Starting Telegram bot with pyTelegramBotAPI...")
        
        import telebot
        from bot_handlers import setup_bot_handlers
        
        bot = telebot.TeleBot(BOT_TOKEN)
        setup_bot_handlers(bot)
        
        logger.info("✅ Bot handlers setup completed")
        logger.info("🔍 Starting polling...")
        
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
        
    except Exception as e:
        logger.error(f"❌ Bot failed to start: {e}")
        import traceback
        logger.error(traceback.format_exc())

def self_ping():
    """Функция для самопинга приложения"""
    while True:
        try:
            # URL вашего приложения
            app_url = "https://tolyatti-fencing-bot.onrender.com"
            response = requests.get(f"{app_url}/health", timeout=10)
            logger.info(f"✅ Self-ping successful: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Self-ping failed: {e}")
        
        # Пинг каждые 10 минут (600 секунд)
        time.sleep(600)

# Запускаем бота только если токен установлен
if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE':
    logger.info("🚀 Starting bot thread...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем самопинг в отдельном потоке
    logger.info("🔄 Starting self-ping thread...")
    ping_thread = threading.Thread(target=self_ping, daemon=True)
    ping_thread.start()
else:
    logger.error("❌ BOT_TOKEN not configured!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

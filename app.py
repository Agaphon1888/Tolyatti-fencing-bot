import os
import logging
import threading
import time
from flask import Flask, request
import requests
import telebot
from telebot import types
from config import BOT_TOKEN, PORT
from bot_handlers import setup_bot_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = None

def setup_bot():
    """Настройка бота и вебхука"""
    global bot
    
    try:
        # Создаем экземпляр бота
        bot = telebot.TeleBot(BOT_TOKEN)
        
        # Настраиваем обработчики
        setup_bot_handlers(bot)
        
        # Устанавливаем вебхук
        webhook_url = f"https://tolyatti-fencing-bot.onrender.com/webhook"
        logger.info(f"🔧 Setting webhook to: {webhook_url}")
        
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        
        logger.info(f"✅ Bot setup completed. Webhook: {webhook_url}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Bot setup failed: {e}")
        return False

def self_ping():
    """Самопинг для поддержания активности"""
    def ping_loop():
        while True:
            try:
                response = requests.get("https://tolyatti-fencing-bot.onrender.com/health", timeout=10)
                logger.info(f"✅ Self-ping successful: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Self-ping failed: {e}")
            time.sleep(300)  # 5 минут
    
    thread = threading.Thread(target=ping_loop, daemon=True)
    thread.start()
    logger.info("🔄 Self-ping thread started")

@app.route('/')
def home():
    return "🤺 Fencing Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/ping')
def ping():
    return "PONG"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик вебхуков от Telegram"""
    global bot
    if bot is None:
        logger.error("❌ Bot is None in webhook")
        return "Bot not initialized", 500
        
    try:
        json_data = request.get_json()
        logger.info(f"📨 Received update: {json_data}")
        
        update = types.Update.de_json(json_data)
        bot.process_new_updates([update])
        
        logger.info("✅ Update processed successfully")
        return "OK"
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}", exc_info=True)
        return "Error", 500

# Инициализация бота при импорте
if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE':
    logger.info("🚀 Initializing bot...")
    if setup_bot():
        logger.info("✅ Bot initialized successfully")
        self_ping()
    else:
        logger.error("❌ Bot initialization failed")
else:
    logger.error("❌ BOT_TOKEN not configured!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

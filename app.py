import os
import logging
from flask import Flask, request, jsonify
import requests
from config import BOT_TOKEN, PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Глобальная переменная для бота
bot = None

def setup_bot():
    """Настройка бота и вебхука"""
    global bot
    
    try:
        import telebot
        from bot_handlers import setup_bot_handlers
        
        # Создаем экземпляр бота
        bot = telebot.TeleBot(BOT_TOKEN)
        
        # Настраиваем обработчики
        setup_bot_handlers(bot)
        
        # Устанавливаем вебхук
        webhook_url = f"https://tolyatti-fencing-bot.onrender.com/webhook"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        
        logger.info(f"✅ Bot setup completed. Webhook: {webhook_url}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Bot setup failed: {e}")
        return False

@app.route('/')
def home():
    return "🤺 Fencing Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/ping')
def ping():
    return "PONG"

@app.route('/status')
def status():
    return {
        "status": "running", 
        "bot_configured": bot is not None,
        "webhook_info": get_webhook_info() if bot else "Bot not configured"
    }

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик вебхуков от Telegram"""
    if bot is None:
        return "Bot not initialized", 500
        
    try:
        json_data = request.get_json()
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return "OK"
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

def get_webhook_info():
    """Получение информации о вебхуке"""
    try:
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo")
        return response.json()
    except Exception as e:
        return f"Error: {e}"

def self_ping():
    """Самопинг для поддержания активности"""
    import time
    import threading
    
    def ping_loop():
        while True:
            try:
                requests.get("https://tolyatti-fencing-bot.onrender.com/health", timeout=10)
                logger.info("✅ Self-ping successful")
            except Exception as e:
                logger.error(f"❌ Self-ping failed: {e}")
            time.sleep(480)  # 8 минут
    
    thread = threading.Thread(target=ping_loop, daemon=True)
    thread.start()
    logger.info("🔄 Self-ping thread started")

# Инициализация при старте
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

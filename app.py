import os
import logging
from flask import Flask, request
import threading
import time
import requests
import atexit
import signal
import sys
from config import BOT_TOKEN, PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Глобальные переменные
bot_thread = None
ping_thread = None
bot_instance = None

@app.route('/')
def home():
    user_agent = request.headers.get('User-Agent', 'Unknown')
    logger.info(f"📄 Root page accessed by: {user_agent}")
    return "🤺 Fencing Bot is running!"

@app.route('/health')
def health():
    user_agent = request.headers.get('User-Agent', 'Unknown')
    logger.info(f"❤️ Health check from: {user_agent}")
    return "OK"

@app.route('/ping')
def ping():
    """Дополнительный эндпоинт для пинга"""
    return "PONG"

@app.route('/status')
def status():
    """Статус приложения"""
    return {
        "status": "running",
        "bot_active": bot_instance is not None,
        "timestamp": time.time()
    }

@app.route('/webhook', methods=['POST'])
def webhook():
    return "OK"

def run_bot_with_retry():
    """Запуск бота с повторными попытками при конфликте"""
    max_retries = 3
    retry_delay = 30  # секунды
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🚀 Attempting to start bot {attempt + 1}/{max_retries}...")
            
            # Закрываем предыдущие соединения через API
            if attempt == 0:
                close_previous_connections()
            
            import telebot
            from bot_handlers import setup_bot_handlers
            
            global bot_instance
            bot_instance = telebot.TeleBot(BOT_TOKEN)
            setup_bot_handlers(bot_instance)
            
            logger.info("✅ Bot handlers configured successfully")
            logger.info("🔍 Starting polling...")
            
            # Используем polling с обработкой ошибок
            bot_instance.polling(
                none_stop=True, 
                timeout=60, 
                long_polling_timeout=60,
                interval=1
            )
            
            logger.info("✅ Polling completed successfully")
            return
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Bot error (attempt {attempt + 1}/{max_retries}): {error_msg}")
            
            if "Conflict: terminated by other getUpdates request" in error_msg:
                logger.warning("🔄 Conflict detected - another bot instance is running")
                if attempt < max_retries - 1:
                    logger.info(f"⏳ Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    # Увеличиваем задержку для следующей попытки
                    retry_delay *= 2
                else:
                    logger.error("❌ Max retries reached. Bot cannot start due to conflict.")
                    break
            else:
                logger.error("❌ Unexpected error, stopping retries.")
                break

def close_previous_connections():
    """Закрывает предыдущие соединения через Telegram API"""
    try:
        import requests as req
        # Закрываем webhook (если был установлен)
        req.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
        logger.info("✅ Previous webhook connections closed")
        
        # Закрываем предыдущие getUpdates
        req.post(f"https://api.telegram.org/bot{BOT_TOKEN}/close")
        logger.info("✅ Previous getUpdates connections closed")
        
        time.sleep(2)  # Даем время на закрытие соединений
    except Exception as e:
        logger.warning(f"⚠️ Could not close previous connections: {e}")

def run_bot():
    """Запуск бота в отдельном потоке"""
    try:
        run_bot_with_retry()
    except Exception as e:
        logger.error(f"❌ Critical bot error: {e}")
        import traceback
        logger.error(traceback.format_exc())

def self_ping():
    """Функция для самопинга приложения"""
    app_url = "https://tolyatti-fencing-bot.onrender.com"
    
    while True:
        try:
            response = requests.get(f"{app_url}/health", timeout=10)
            logger.info(f"✅ Self-ping successful: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Self-ping failed: {e}")
        
        # Пинг каждые 8 минут (меньше 15 минут сна Render)
        time.sleep(480)

def stop_bot():
    """Корректная остановка бота"""
    try:
        global bot_instance
        if bot_instance:
            logger.info("🛑 Stopping bot...")
            bot_instance.stop_polling()
            logger.info("✅ Bot stopped successfully")
    except Exception as e:
        logger.error(f"❌ Error stopping bot: {e}")

def stop_ping():
    """Остановка пинга"""
    global ping_thread
    if ping_thread and ping_thread.is_alive():
        logger.info("🛑 Stopping ping thread...")

def cleanup():
    """Очистка ресурсов при завершении"""
    logger.info("🧹 Cleaning up resources...")
    stop_bot()
    stop_ping()

def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    logger.info(f"📞 Received signal {signum}, shutting down...")
    cleanup()
    sys.exit(0)

# Регистрируем обработчики для корректного завершения
atexit.register(cleanup)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Основной запуск
if __name__ == '__main__':
    # Запускаем бота только если токен установлен
    if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE':
        logger.info("🚀 Starting bot thread...")
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        
        # Запускаем самопинг в отдельном потоке
        logger.info("🔄 Starting self-ping thread...")
        ping_thread = threading.Thread(target=self_ping, daemon=True)
        ping_thread.start()
        
        # Запускаем Flask приложение
        app.run(host='0.0.0.0', port=PORT, debug=False)
    else:
        logger.error("❌ BOT_TOKEN not configured!")
        # Все равно запускаем Flask для мониторинга
        app.run(host='0.0.0.0', port=PORT, debug=False)

import os
import logging
from flask import Flask
import threading
import asyncio
from config import BOT_TOKEN, PORT

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
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

async def run_bot_async():
    """Асинхронный запуск бота"""
    try:
        from telegram.ext import Updater
        from handlers import setup_handlers
        
        logger.info("🤖 Creating bot application...")
        
        # Используем Updater для версии 13.x
        updater = Updater(token=BOT_TOKEN, use_context=True)
        
        # Настраиваем обработчики
        setup_handlers(updater)
        
        logger.info("🔍 Starting polling...")
        updater.start_polling()
        logger.info("✅ Bot started successfully with polling!")
        
        # Бесконечный цикл для поддержания работы
        while True:
            await asyncio.sleep(3600)  # Спим 1 час
            
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        import traceback
        logger.error(traceback.format_exc())

def run_bot():
    """Запуск бота в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_async())

# Запускаем бота только если токен установлен
if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE':
    logger.info("🚀 Starting bot thread...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
else:
    logger.error("❌ BOT_TOKEN not configured!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

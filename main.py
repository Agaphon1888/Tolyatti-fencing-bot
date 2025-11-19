import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import threading
import asyncio
from handlers import setup_handlers
from config import BOT_TOKEN, PORT

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask приложение для веб-сервера
app = Flask(__name__)

@app.route('/')
def home():
    return "🤺 Fencing Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/webhook', methods=['POST'])
def webhook():
    # Для будущей интеграции с вебхуками
    return "OK"

# Глобальная переменная для бота
bot_application = None

async def main():
    """Запуск телеграм бота"""
    global bot_application
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Настраиваем обработчики
    setup_handlers(application)
    
    # Сохраняем ссылку на application
    bot_application = application
    
    # Запускаем бота
    logger.info("Бот запускается...")
    await application.run_polling()

def run_bot():
    """Запуск бота в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask приложение
    app.run(host='0.0.0.0', port=PORT, debug=False)

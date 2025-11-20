import os
import logging
from flask import Flask, request
import telebot
from telebot import types
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
logger.info(f"🔧 BOT_TOKEN: {'***' + BOT_TOKEN[-4:] if BOT_TOKEN else 'NOT SET'}")

# Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

# Диагностика - проверим все зарегистрированные обработчики
def log_handlers():
    logger.info("🔍 Registered handlers:")
    for handler in bot.message_handlers:
        logger.info(f"   - {handler}")

# Простой обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    user = message.from_user
    logger.info(f"👤 MINIMAL: User {user.id} started the bot - HANDLER EXECUTED")
    
    welcome_text = """
🤺 Добро пожаловать в <b>Тольяттинскую федерацию фехтования</b>!

Это тестовое сообщение. Бот работает!

Команда /start обработана успешно!
    """
    
    try:
        sent_message = bot.send_message(message.chat.id, welcome_text, parse_mode='HTML')
        logger.info(f"✅ MINIMAL: Start message sent to user {user.id}, message_id: {sent_message.message_id}")
    except Exception as e:
        logger.error(f"❌ MINIMAL: Failed to send start message: {e}")

# Обработчик для всех сообщений для диагностики
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    logger.info(f"🔍 ECHO: Received message from {message.from_user.id}: {message.text}")
    bot.reply_to(message, f"Эхо: {message.text}")

@app.route('/')
def home():
    return "🤺 Fencing Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/debug')
def debug():
    """Страница диагностики"""
    try:
        webhook_info = bot.get_webhook_info()
        return {
            "bot_token_set": bool(BOT_TOKEN),
            "webhook_info": {
                "url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count
            },
            "handlers_count": len(bot.message_handlers),
            "status": "running"
        }
    except Exception as e:
        return {"error": str(e)}

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик вебхуков от Telegram"""
    try:
        json_data = request.get_json()
        logger.info(f"📨 MINIMAL: Received update ID: {json_data.get('update_id')}")
        
        update = types.Update.de_json(json_data)
        
        # Логируем тип обновления
        if update.message:
            logger.info(f"💬 Message from {update.message.from_user.id}: {update.message.text}")
        elif update.callback_query:
            logger.info(f"🔘 Callback from {update.callback_query.from_user.id}: {update.callback_query.data}")
        
        # Обрабатываем обновление
        bot.process_new_updates([update])
        
        logger.info("✅ MINIMAL: Update processed successfully")
        return "OK"
    except Exception as e:
        logger.error(f"❌ MINIMAL: Webhook error: {e}", exc_info=True)
        return "Error", 500

# Установка вебхука при старте
if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE':
    try:
        webhook_url = f"https://tolyatti-fencing-bot.onrender.com/webhook"
        logger.info(f"🔧 Setting webhook to: {webhook_url}")
        
        # Даем время на запуск сервера
        time.sleep(2)
        
        bot.remove_webhook()
        time.sleep(1)
        result = bot.set_webhook(url=webhook_url)
        
        logger.info(f"✅ MINIMAL: Webhook set successfully: {result}")
        
        # Логируем зарегистрированные обработчики
        log_handlers()
        
    except Exception as e:
        logger.error(f"❌ MINIMAL: Failed to set webhook: {e}")
else:
    logger.error("❌ MINIMAL: BOT_TOKEN not configured!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

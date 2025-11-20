import os
import logging
from flask import Flask, request
import telebot
from telebot import types
import time
import threading

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
        
        # Используем альтернативный метод обработки
        update = types.Update.de_json(json_data)
        
        # Логируем тип обновления
        if update.message:
            logger.info(f"💬 Message from {update.message.from_user.id}: {update.message.text}")
            
            # Пробуем разные методы обработки
            try:
                # Метод 1: Прямой вызов process_new_messages
                logger.info("🔄 Trying process_new_messages...")
                bot.process_new_messages([update.message])
            except Exception as e1:
                logger.error(f"❌ process_new_messages failed: {e1}")
                try:
                    # Метод 2: Ручной вызов обработчиков
                    logger.info("🔄 Trying manual handler execution...")
                    for handler in bot.message_handlers:
                        if handler['check'](update.message):
                            logger.info(f"✅ Executing handler: {handler}")
                            handler['function'](update.message)
                            break
                except Exception as e2:
                    logger.error(f"❌ Manual handler execution failed: {e2}")
                    
        elif update.callback_query:
            logger.info(f"🔘 Callback from {update.callback_query.from_user.id}: {update.callback_query.data}")
            bot.process_new_callback_query([update.callback_query])
        
        logger.info("✅ MINIMAL: Update processed successfully")
        return "OK"
    except Exception as e:
        logger.error(f"❌ MINIMAL: Webhook error: {e}", exc_info=True)
        return "Error", 500

# Функция для отправки сообщения напрямую через API
def send_message_directly(chat_id, text):
    """Отправка сообщения напрямую через Telegram API"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload)
        logger.info(f"📤 Direct API response: {response.status_code}")
        return response.json()
    except Exception as e:
        logger.error(f"❌ Direct API failed: {e}")

# Альтернативный маршрут вебхука с прямой отправкой
@app.route('/webhook2', methods=['POST'])
def webhook2():
    """Альтернативный обработчик вебхуков"""
    try:
        json_data = request.get_json()
        logger.info(f"📨 WEBHOOK2: Received update")
        
        if 'message' in json_data:
            message = json_data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            logger.info(f"💬 WEBHOOK2: Message from {chat_id}: {text}")
            
            if text == '/start':
                response = send_message_directly(chat_id, 
                    "🤺 Добро пожаловать! Это сообщение отправлено напрямую через API!")
                logger.info(f"✅ WEBHOOK2: Direct message sent: {response}")
        
        return "OK"
    except Exception as e:
        logger.error(f"❌ WEBHOOK2 error: {e}")
        return "Error", 500

# Установка вебхука при старте
if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE':
    try:
        webhook_url = f"https://tolyatti-fencing-bot.onrender.com/webhook"
        logger.info(f"🔧 Setting webhook to: {webhook_url}")
        
        time.sleep(2)
        bot.remove_webhook()
        time.sleep(1)
        result = bot.set_webhook(url=webhook_url)
        
        logger.info(f"✅ MINIMAL: Webhook set successfully: {result}")
        log_handlers()
        
    except Exception as e:
        logger.error(f"❌ MINIMAL: Failed to set webhook: {e}")
else:
    logger.error("❌ MINIMAL: BOT_TOKEN not configured!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

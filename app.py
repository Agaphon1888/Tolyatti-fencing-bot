import os
import logging
from flask import Flask, request
import telebot
from telebot import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# Простой обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    user = message.from_user
    logger.info(f"👤 MINIMAL: User {user.id} started the bot")
    
    welcome_text = """
🤺 Добро пожаловать в <b>Тольяттинскую федерацию фехтования</b>!

Это тестовое сообщение. Бот работает!
    """
    
    try:
        bot.send_message(message.chat.id, welcome_text, parse_mode='HTML')
        logger.info(f"✅ MINIMAL: Start message sent to user {user.id}")
    except Exception as e:
        logger.error(f"❌ MINIMAL: Failed to send start message: {e}")

@app.route('/')
def home():
    return "🤺 Fencing Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик вебхуков от Telegram"""
    try:
        json_data = request.get_json()
        logger.info(f"📨 MINIMAL: Received update: {json_data}")
        
        update = types.Update.de_json(json_data)
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
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        logger.info(f"✅ MINIMAL: Webhook set to: {webhook_url}")
    except Exception as e:
        logger.error(f"❌ MINIMAL: Failed to set webhook: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

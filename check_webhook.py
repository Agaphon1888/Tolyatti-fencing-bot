import requests
import os
from config import BOT_TOKEN

def check_webhook():
    """Проверка состояния вебхука"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    response = requests.get(url)
    return response.json()

if __name__ == '__main__':
    result = check_webhook()
    print("Webhook status:", result)

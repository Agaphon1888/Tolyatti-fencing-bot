import os
from dotenv import load_dotenv

load_dotenv()

# Конфигурация бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable is required")

# Список администраторов
ADMINS_STR = os.getenv('ADMINS', '')
ADMINS = []
if ADMINS_STR:
    ADMINS = [int(admin_id.strip()) for admin_id in ADMINS_STR.split(',') if admin_id.strip().isdigit()]

PORT = int(os.getenv('PORT', 5000))

# Получаем URL для вебхука
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL', 'https://tolyatti-fencing-bot.onrender.com')

# Данные организации
ORG_INFO = {
    'full_name': 'Автономная некоммерческая организация "Тольяттинская федерация фехтования"',
    'short_name': 'АНО "Тольяттинская федерация фехтования"',
    'inn': '6320267029',
    'kpp': '632001001',
    'ogrn': '1146300002793',
    'account': '40703810212300001063',
    'bank': 'ОАО АКБ "Авангард"',
    'bik': '044525201',
    'correspondent_account': '3010181000000000201'
}

# ... остальной код без изменений

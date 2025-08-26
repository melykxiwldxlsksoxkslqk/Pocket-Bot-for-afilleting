import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from app.admin.admin_panel import AdminPanel
from app.services.telethon_code import telethon_client  # Import the instance directly
from app.services.trading_api import TradingAPI

# Загружаем переменные окружения из .env файла
load_dotenv()

# --- Загрузка и проверка обязательных переменных окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле. Пожалуйста, добавьте его.")
if not ADMIN_IDS_RAW:
    raise ValueError("ADMIN_IDS не найден в .env файле. Пожалуйста, добавьте его.")

try:
    # Преобразуем строку ID администраторов в список целых чисел
    admin_ids_list = [int(id) for id in ADMIN_IDS_RAW.split(',') if id.strip()]
except ValueError:
    raise ValueError("ADMIN_IDS должен быть списком чисел, разделенных запятыми (например, 123,456).")

# --- Инициализация компонентов ---

# Инициализация бота и диспетчера
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Инициализация панели администратора
admin_panel = AdminPanel(admin_ids=admin_ids_list)

# Инициализация Trading API
trading_api = TradingAPI()
trading_api.set_admin_panel(admin_panel)
trading_api.set_telethon_client(telethon_client) # Pass the wrapper instance
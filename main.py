import os
import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

import sheets
import handlers

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(',') if x.strip()]

if not API_TOKEN:
    raise EnvironmentError("API_TOKEN is not set")
if not CREDENTIALS_FILE:
    raise EnvironmentError("CREDENTIALS_FILE is not set")
if not ADMIN_IDS:
    raise EnvironmentError("ADMIN_IDS is not set")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

handlers.register_handlers(dp, bot, ADMIN_IDS)

if __name__ == "__main__":
    sheets.init_gspread(CREDENTIALS_FILE)
    print("[LOG] Бот запущено")
    asyncio.run(dp.start_polling(bot))


import os
import asyncio
from aiogram import Bot
from dotenv import load_dotenv

from sheets import init_gspread
import handlers

bot: Bot | None = None


def main() -> None:
    global bot
    load_dotenv()

    api_token = os.getenv("API_TOKEN")
    credentials_file = os.getenv("CREDENTIALS_FILE")
    admin_ids = [int(x) for x in os.getenv("ADMIN_IDS", "").split(',') if x.strip()]

    if not api_token:
        raise EnvironmentError("API_TOKEN is not set")
    if not credentials_file:
        raise EnvironmentError("CREDENTIALS_FILE is not set")
    if not admin_ids:
        raise EnvironmentError("ADMIN_IDS is not set")

    bot = Bot(token=api_token)

    handlers.bot = bot
    handlers.ADMIN_IDS = admin_ids

    init_gspread(credentials_file)

    print("[LOG] Бот запущено")
    asyncio.run(handlers.dp.start_polling(bot))


if __name__ == "__main__":
    main()

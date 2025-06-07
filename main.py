import os
import sys
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from aiogram import Bot
from dotenv import load_dotenv

from sheets import init_gspread
import handlers

bot: Bot | None = None


def configure_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    file_handler = RotatingFileHandler(
        "logs/bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stderr_handler)


def main() -> None:
    global bot
    configure_logging()
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

    logging.getLogger(__name__).info("Бот запущено")
    asyncio.run(handlers.dp.start_polling(bot))


if __name__ == "__main__":
    main()

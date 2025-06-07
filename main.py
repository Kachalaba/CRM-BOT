import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler

from aiogram import Bot
from dotenv import load_dotenv

import handlers
from sheets import init_gspread

bot: Bot | None = None


def setup_logging() -> None:
    """Configure logging to file and stderr."""
    os.makedirs("logs", exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    file_handler = RotatingFileHandler(
        "logs/bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [file_handler, stream_handler]


def main() -> None:
    global bot
    load_dotenv()

    setup_logging()

    api_token = os.getenv("API_TOKEN")
    credentials_file = os.getenv("CREDENTIALS_FILE")
    admin_ids = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

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

    logging.info("Бот запущено")
    asyncio.run(handlers.dp.start_polling(bot))


if __name__ == "__main__":
    main()

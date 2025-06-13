import asyncio
import logging
import os
import platform
import signal
from logging.handlers import RotatingFileHandler

from aiogram import Bot
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

import handlers  # noqa: E402
from sheets import init_gspread  # noqa: E402

bot: Bot | None = None


async def shutdown() -> None:
    """Gracefully stop polling and close gspread session."""
    await handlers.dp.stop_polling()
    logging.info("Bot stopped")


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

    setup_logging()

    api_token = os.getenv("API_TOKEN")
    credentials_file = os.getenv("CREDENTIALS_FILE")
    admin_ids = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

    if not api_token:
        raise EnvironmentError("API_TOKEN is not set")
    if not credentials_file or not os.path.exists(credentials_file):
        logger.warning(
            "⚠️  creds.json not found – положи JSON и пропиши CREDENTIALS_FILE"
        )
        raise SystemExit(1)
    if not admin_ids:
        raise EnvironmentError("ADMIN_IDS is not set")

    bot = Bot(token=api_token)

    handlers.bot = bot
    handlers.ADMIN_IDS = admin_ids

    logger.info("Бот запущено")

    async def run() -> None:
        await init_gspread(credentials_file)
        loop = asyncio.get_running_loop()
        if platform.system() != "Windows":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
        await handlers.dp.start_polling(bot)

    asyncio.run(run())


if __name__ == "__main__":
    main()

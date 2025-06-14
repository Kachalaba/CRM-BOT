# handlers.py (ВИПРАВЛЕНА ВЕРСІЯ)

import logging
import random
import time
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

# Ось головні зміни:
import sheets  # Імпортуємо весь модуль, а не окремі змінні
from sheets import get_client_name  # Функції можна імпортувати напряму
from utils.i18n import t

logger = logging.getLogger(__name__)

bot: Bot | None = None
ADMIN_ID: str | None = None

STATS_CACHE: dict[str, tuple[float, int]] = {}

RENT_COST_PER_SESSION = 330

dp = Dispatcher()
router = Router()


@router.message(lambda message: message.contact)
async def register_by_contact(message: types.Message):
    user_id = str(message.contact.user_id)
    name = message.contact.first_name or "Клієнт"
    # Звертаємося через sheets.clients_sheet
    records = await sheets.clients_sheet.get_all_records()
    if records is None:
        await message.answer(
            "❗ Виникла помилка під час роботи з базою даних. Спробуйте пізніше."
        )
        return
    if any(str(row["ID"]) == user_id for row in records):
        await message.answer(t("❗ Ви вже зареєстровані.", user=message.from_user))
        return
    end_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    await sheets.clients_sheet.append_row([user_id, name, 10, end_date, "-"])
    logger.info("Зареєстровано нового користувача: %s (%s)", user_id, name)
    await message.answer(
        t(
            "✅ Реєстрація успішна! Вам додано 10 занять на 60 днів.",
            user=message.from_user,
        )
    )


@router.message(Command(commands=["start"]))
async def send_welcome(message: types.Message, admin_id: str):
    keyboard = [
        [InlineKeyboardButton(text="📊 Мої заняття", callback_data="my_sessions")],
        [InlineKeyboardButton(text="📜 Історія занять", callback_data="view_history")],
        [
            InlineKeyboardButton(
                text="💳 Отримати абонемент", callback_data="request_subscription"
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Відмітити заняття", callback_data="mark_session"
            )
        ],
        [InlineKeyboardButton(text="😼 Таємна кнопка", callback_data="secret_button")],
    ]
    if str(message.from_user.id) == admin_id:
        keyboard.insert(
            0,
            [
                InlineKeyboardButton(
                    text="🔧 Панель адміністратора", callback_data="admin_panel"
                )
            ],
        )
    await message.answer(
        t("/start", user=message.from_user),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await message.answer(t("/help", user=message.from_user))
    logger.info("User %s used /start", message.from_user.id)


@router.message(Command(commands=["help"]))
async def send_help(message: types.Message) -> None:
    """Send available bot commands."""
    await message.answer(t("/help", user=message.from_user))


@router.message(Command(commands=["ping"]))
async def ping(message: types.Message) -> None:
    """Reply with pong and response time."""
    start = time.monotonic()
    sent = await message.answer(t("pong", user=message.from_user))
    latency = int((time.monotonic() - start) * 1000)
    await sent.edit_text(f"pong {latency} ms")
    logger.info("User %s used /ping", message.from_user.id)


@router.message(Command(commands=["stats"]))
async def stats(message: types.Message) -> None:
    """Show remaining sessions for the user with caching."""
    now = time.monotonic()
    user_id = str(message.from_user.id)
    cached = STATS_CACHE.get(user_id)
    if cached and now - cached[0] < 30:
        await message.answer(
            t("У тебя {count} оставшихся", user=message.from_user, count=cached[1])
        )
        logger.info("User %s used /stats (cache)", message.from_user.id)
        return

    records = await sheets.clients_sheet.get_all_records()
    if records is None:
        await message.answer(
            "❗ Виникла помилка під час роботи з базою даних. Спробуйте пізніше."
        )
        return
    for row in records:
        if str(row["ID"]) == user_id:
            count = int(row["К-сть тренувань"])
            STATS_CACHE[user_id] = (now, count)
            await message.answer(
                t("У тебя {count} оставшихся", user=message.from_user, count=count)
            )
            logger.info("User %s used /stats", message.from_user.id)
            return
    await message.answer(t("❗ Ви ще не зареєстровані.", user=message.from_user))


@router.callback_query(lambda c: c.data == "my_sessions")
async def my_sessions(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    records = await sheets.clients_sheet.get_all_records()
    if records is None:
        await callback.message.answer(
            "❗ Виникла помилка під час роботи з базою даних. Спробуйте пізніше."
        )
        return
    for row in records:
        if str(row["ID"]) == user_id:
            logger.info("Перевірка занять для %s", user_id)
            await callback.message.answer(
                t(
                    "У вас залишилось {count} занять. Термін дії: {date}",
                    user=callback.from_user,
                    count=row["К-сть тренувань"],
                    date=row["Кінцева дата"],
                )
            )
            return
    await callback.message.answer(
        t("❗ Ви ще не зареєстровані.", user=callback.from_user)
    )


@router.callback_query(lambda c: c.data == "view_history")
async def view_history(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    rows = await sheets.history_sheet.get_all_values()
    if rows is None:
        await callback.message.answer(
            "❗ Виникла помилка під час роботи з базою даних. Спробуйте пізніше."
        )
        return
    lines = [f"{row[1]} – {row[2]}" for row in rows if row[0] == user_id]
    await callback.message.answer(
        "\n".join(lines) if lines else t("Історія пуста.", user=callback.from_user)
    )


@router.callback_query(lambda c: c.data == "mark_session")
async def mark_session(callback: CallbackQuery, admin_id: str):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Підтвердити",
                    callback_data=f"approve_deduction:{callback.from_user.id}",
                ),
                InlineKeyboardButton(
                    text="❌ Скасувати", callback_data="cancel_request"
                ),
            ]
        ]
    )
    logger.info("Отримано запит на списання заняття від %s", callback.from_user.id)
    await bot.send_message(
        admin_id,
        f"Запит на списання заняття від {callback.from_user.id}",
        reply_markup=keyboard,
    )
    await callback.message.answer(
        t("✅ Запит надіслано адміну", user=callback.from_user)
    )


@router.callback_query(lambda c: c.data == "cancel_request")
async def cancel_request(callback: CallbackQuery):
    await callback.message.edit_text(t("Запит скасовано.", user=callback.from_user))


@router.callback_query(lambda c: c.data.startswith("approve_deduction:"))
async def approve_deduction(callback: CallbackQuery):
    user_id = callback.data.split(":")[1]
    records = await sheets.clients_sheet.get_all_records()
    if records is None:
        await callback.message.answer(
            "❗ Виникла помилка під час роботи з базою даних. Спробуйте пізніше."
        )
        return
    for idx, row in enumerate(records):
        if str(row["ID"]) == user_id:
            new_sessions = max(0, int(row["К-сть тренувань"]) - 1)
            await sheets.clients_sheet.update_cell(idx + 2, 3, new_sessions)
            await sheets.history_sheet.append_row(
                [
                    user_id,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Списано 1 заняття",
                ]
            )
            name = get_client_name(row)
            logger.info("Списано 1 заняття для %s, залишок: %s", user_id, new_sessions)
            await bot.send_message(
                user_id,
                t(
                    "❗ Списано 1 заняття. Залишок: {count}",
                    user=callback.from_user,
                    count=new_sessions,
                ),
            )
            await callback.message.answer(
                t(
                    "Списано для {name} (ID: {user_id})",
                    user=callback.from_user,
                    name=name,
                    user_id=user_id,
                )
            )
            return
    await callback.message.answer(t("Клієнт не знайдений", user=callback.from_user))


@router.callback_query(lambda c: c.data == "request_subscription")
async def request_subscription(callback: CallbackQuery, admin_id: str):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Дати 10 занять",
                    callback_data=f"approve_subscription:{callback.from_user.id}",
                ),
                InlineKeyboardButton(
                    text="❌ Відмовити", callback_data="deny_subscription"
                ),
            ]
        ]
    )
    logger.info("Клієнт %s запитав абонемент", callback.from_user.id)
    await bot.send_message(
        admin_id,
        f"Запит на новий абонемент від {callback.from_user.id}",
        reply_markup=keyboard,
    )
    await callback.message.answer(
        t("💳 Запит надіслано адміну", user=callback.from_user)
    )


@router.callback_query(lambda c: c.data == "deny_subscription")
async def deny_subscription(callback: CallbackQuery):
    await callback.message.edit_text(
        t("❌ Запит на абонемент відхилено.", user=callback.from_user)
    )


@router.callback_query(lambda c: c.data.startswith("approve_subscription:"))
async def approve_subscription(callback: CallbackQuery):
    user_id = callback.data.split(":")[1]
    records = await sheets.clients_sheet.get_all_records()
    if records is None:
        await callback.message.answer(
            "❗ Виникла помилка під час роботи з базою даних. Спробуйте пізніше."
        )
        return
    for idx, row in enumerate(records):
        if str(row["ID"]) == user_id:
            await sheets.clients_sheet.update_cell(idx + 2, 3, 10)
            new_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
            await sheets.clients_sheet.update_cell(idx + 2, 4, new_date)
            await sheets.history_sheet.append_row(
                [
                    user_id,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Додано 10 занять",
                ]
            )
            logger.info("Додано 10 занять користувачу %s", user_id)
            await bot.send_message(
                user_id,
                t(
                    "🎉 Вам видано новий абонемент на 10 занять (60 днів)",
                    user=callback.from_user,
                ),
            )
            await callback.message.answer(
                t(
                    "Видано новий абонемент для ID {user_id}",
                    user=callback.from_user,
                    user_id=user_id,
                )
            )
            return
    await callback.message.answer(t("Клієнт не знайдений", user=callback.from_user))


@router.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    clients = await sheets.clients_sheet.get_all_records()
    if clients is None:
        await callback.message.answer(
            "❗ Виникла помилка під час роботи з базою даних. Спробуйте пізніше."
        )
        return
    reserve_total = 0
    for client in clients:
        user_id = client["ID"]
        name = get_client_name(client)
        sessions = int(client["К-сть тренувань"])
        reserve_total += sessions * RENT_COST_PER_SESSION
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Додати", callback_data=f"add_session:{user_id}"
                    ),
                    InlineKeyboardButton(
                        text="➖ Списати", callback_data=f"approve_deduction:{user_id}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="📜 Історія", callback_data=f"history:{user_id}"
                    )
                ],
            ]
        )
        await callback.message.answer(
            t(
                "👤 {name} (ID: {user_id})\nЗалишок: {sessions}",
                user=callback.from_user,
                name=name,
                user_id=user_id,
                sessions=sessions,
            ),
            reply_markup=keyboard,
        )
    await callback.message.answer(
        t(
            "💰 Сума, яку потрібно тримати для оренди: {amount} грн",
            user=callback.from_user,
            amount=reserve_total,
        )
    )


@router.callback_query(lambda c: c.data.startswith("add_session:"))
async def add_session(callback: CallbackQuery):
    user_id = callback.data.split(":")[1]
    records = await sheets.clients_sheet.get_all_records()
    if records is None:
        await callback.message.answer(
            "❗ Виникла помилка під час роботи з базою даних. Спробуйте пізніше."
        )
        return
    for idx, row in enumerate(records):
        if str(row["ID"]) == user_id:
            new_sessions = int(row["К-сть тренувань"]) + 1
            await sheets.clients_sheet.update_cell(idx + 2, 3, new_sessions)
            if not row.get("Ім’я"):
                await sheets.clients_sheet.update_cell(idx + 2, 2, "Клієнт")
            await sheets.history_sheet.append_row(
                [user_id, datetime.now().strftime("%Y-%m-%d %H:%M"), "Додано 1 заняття"]
            )
            await bot.send_message(
                user_id,
                t(
                    "➕ Вам додано 1 заняття. Тепер у вас {count}",
                    user=callback.from_user,
                    count=new_sessions,
                ),
            )
            await callback.message.answer(t("Заняття додано", user=callback.from_user))
            return


@router.callback_query(lambda c: c.data.startswith("history:"))
async def user_history(callback: CallbackQuery):
    user_id = callback.data.split(":")[1]
    rows = await sheets.history_sheet.get_all_values()
    if rows is None:
        await callback.message.answer(
            "❗ Виникла помилка під час роботи з базою даних. Спробуйте пізніше."
        )
        return
    lines = [f"{row[1]} – {row[2]}" for row in rows if row[0] == user_id]
    await callback.message.answer(
        "\n".join(lines) if lines else t("Історія пуста.", user=callback.from_user)
    )


@router.callback_query(lambda c: c.data == "secret_button")
async def secret_button(callback: CallbackQuery):
    messages = [
        "😾 Котик незадоволений, що ти натиснув цю кнопку!",
        "🌀 Ти відкрив портал у котячий вимір... але нічого не сталося.",
        "💥 А ти справді думав, що тут щось є?",
        "🐾 Секретів тут нема, тільки хвости.",
    ]
    await callback.message.answer(t(random.choice(messages), user=callback.from_user))


@router.message()
async def unknown_message(message: types.Message) -> None:
    """Handle unknown commands."""
    await message.answer(t("unknown", user=message.from_user))
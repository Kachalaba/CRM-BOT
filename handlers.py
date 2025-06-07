import logging
import random
import time
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from sheets import clients_sheet, get_client_name, history_sheet

bot: Bot | None = None
ADMIN_IDS: list[int] = []

STATS_CACHE: dict[str, tuple[float, int]] = {}

RENT_COST_PER_SESSION = 330

dp = Dispatcher()


@dp.message(lambda message: message.contact)
async def register_by_contact(message: types.Message):
    user_id = str(message.contact.user_id)
    name = message.contact.first_name or "Клієнт"
    records = clients_sheet.get_all_records()
    if any(str(row["ID"]) == user_id for row in records):
        await message.answer("❗ Ви вже зареєстровані.")
        return
    end_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    clients_sheet.append_row([user_id, name, 10, end_date, "-"])
    logging.info("Зареєстровано нового користувача: %s (%s)", user_id, name)
    await message.answer("✅ Реєстрація успішна! Вам додано 10 занять на 60 днів.")


@dp.message(Command(commands=["start"]))
async def send_welcome(message: types.Message):
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
    if message.from_user.id in ADMIN_IDS:
        keyboard.insert(
            0,
            [
                InlineKeyboardButton(
                    text="🔧 Панель адміністратора", callback_data="admin_panel"
                )
            ],
        )
    await message.answer(
        "Вітаю в CRM боті 🐬",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


@dp.message(Command(commands=["help"]))
async def send_help(message: types.Message) -> None:
    """Send available bot commands."""
    commands = [
        "/start - start bot",
        "/help - list available commands",
        "/ping - check bot latency",
        "/stats - show remaining sessions",
    ]
    await message.answer("\n".join(commands))


@dp.message(Command(commands=["ping"]))
async def ping(message: types.Message) -> None:
    """Reply with pong and response time."""
    start = time.monotonic()
    sent = await message.answer("pong")
    latency = int((time.monotonic() - start) * 1000)
    await sent.edit_text(f"pong {latency} ms")


@dp.message(Command(commands=["stats"]))
async def stats(message: types.Message) -> None:
    """Show remaining sessions for the user with caching."""
    now = time.monotonic()
    user_id = str(message.from_user.id)
    cached = STATS_CACHE.get(user_id)
    if cached and now - cached[0] < 30:
        await message.answer(f"У тебя {cached[1]} оставшихся")
        return

    records = clients_sheet.get_all_records()
    for row in records:
        if str(row["ID"]) == user_id:
            count = int(row["К-сть тренувань"])
            STATS_CACHE[user_id] = (now, count)
            await message.answer(f"У тебя {count} оставшихся")
            return
    await message.answer("❗ Ви ще не зареєстровані.")


@dp.callback_query(lambda c: c.data == "my_sessions")
async def my_sessions(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    records = clients_sheet.get_all_records()
    for row in records:
        if str(row["ID"]) == user_id:
            logging.info("Перевірка занять для %s", user_id)
            await callback.message.answer(
                f"У вас залишилось {row['К-сть тренувань']} занять. Термін дії: {row['Кінцева дата']}"
            )
            return
    await callback.message.answer("❗ Ви ще не зареєстровані.")


@dp.callback_query(lambda c: c.data == "view_history")
async def view_history(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    rows = history_sheet.get_all_values()
    lines = [f"{row[1]} – {row[2]}" for row in rows if row[0] == user_id]
    await callback.message.answer("\n".join(lines) if lines else "Історія пуста.")


@dp.callback_query(lambda c: c.data == "mark_session")
async def mark_session(callback: CallbackQuery):
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
    logging.info("Отримано запит на списання заняття від %s", callback.from_user.id)
    await bot.send_message(
        ADMIN_IDS[0],
        f"Запит на списання заняття від {callback.from_user.id}",
        reply_markup=keyboard,
    )
    await callback.message.answer("✅ Запит надіслано адміну")


@dp.callback_query(lambda c: c.data == "cancel_request")
async def cancel_request(callback: CallbackQuery):
    await callback.message.edit_text("Запит скасовано.")


@dp.callback_query(lambda c: c.data.startswith("approve_deduction:"))
async def approve_deduction(callback: CallbackQuery):
    user_id = callback.data.split(":")[1]
    records = clients_sheet.get_all_records()
    for idx, row in enumerate(records):
        if str(row["ID"]) == user_id:
            new_sessions = max(0, int(row["К-сть тренувань"]) - 1)
            clients_sheet.update_cell(idx + 2, 3, new_sessions)
            history_sheet.append_row(
                [
                    user_id,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Списано 1 заняття",
                ]
            )
            name = get_client_name(row)
            logging.info("Списано 1 заняття для %s, залишок: %s", user_id, new_sessions)
            await bot.send_message(
                user_id, f"❗ Списано 1 заняття. Залишок: {new_sessions}"
            )
            await callback.message.answer(f"Списано для {name} (ID: {user_id})")
            return
    await callback.message.answer("Клієнт не знайдений")


@dp.callback_query(lambda c: c.data == "request_subscription")
async def request_subscription(callback: CallbackQuery):
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
    logging.info("Клієнт %s запитав абонемент", callback.from_user.id)
    await bot.send_message(
        ADMIN_IDS[0],
        f"Запит на новий абонемент від {callback.from_user.id}",
        reply_markup=keyboard,
    )
    await callback.message.answer("💳 Запит надіслано адміну")


@dp.callback_query(lambda c: c.data == "deny_subscription")
async def deny_subscription(callback: CallbackQuery):
    await callback.message.edit_text("❌ Запит на абонемент відхилено.")


@dp.callback_query(lambda c: c.data.startswith("approve_subscription:"))
async def approve_subscription(callback: CallbackQuery):
    user_id = callback.data.split(":")[1]
    records = clients_sheet.get_all_records()
    for idx, row in enumerate(records):
        if str(row["ID"]) == user_id:
            clients_sheet.update_cell(idx + 2, 3, 10)
            new_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
            clients_sheet.update_cell(idx + 2, 4, new_date)
            history_sheet.append_row(
                [
                    user_id,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Додано 10 занять",
                ]
            )
            logging.info("Додано 10 занять користувачу %s", user_id)
            await bot.send_message(
                user_id, "🎉 Вам видано новий абонемент на 10 занять (60 днів)"
            )
            await callback.message.answer(f"Видано новий абонемент для ID {user_id}")
            return
    await callback.message.answer("Клієнт не знайдений")


@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    clients = clients_sheet.get_all_records()
    reserve_total = 0
    for client in clients:
        user_id = client["ID"]
        name = get_client_name(client)
        sessions = client["К-сть тренувань"]
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
            f"👤 {name} (ID: {user_id})\nЗалишок: {sessions}", reply_markup=keyboard
        )
    await callback.message.answer(
        f"💰 Сума, яку потрібно тримати для оренди: {reserve_total} грн"
    )


@dp.callback_query(lambda c: c.data.startswith("add_session:"))
async def add_session(callback: CallbackQuery):
    user_id = callback.data.split(":")[1]
    records = clients_sheet.get_all_records()
    for idx, row in enumerate(records):
        if str(row["ID"]) == user_id:
            new_sessions = int(row["К-сть тренувань"]) + 1
            clients_sheet.update_cell(idx + 2, 3, new_sessions)
            if not row.get("Ім’я"):
                clients_sheet.update_cell(idx + 2, 2, "Клієнт")
            history_sheet.append_row(
                [user_id, datetime.now().strftime("%Y-%m-%d %H:%M"), "Додано 1 заняття"]
            )
            await bot.send_message(
                user_id, f"➕ Вам додано 1 заняття. Тепер у вас {new_sessions}"
            )
            await callback.message.answer("Заняття додано")
            return


@dp.callback_query(lambda c: c.data.startswith("history:"))
async def user_history(callback: CallbackQuery):
    user_id = callback.data.split(":")[1]
    rows = history_sheet.get_all_values()
    lines = [f"{row[1]} – {row[2]}" for row in rows if row[0] == user_id]
    await callback.message.answer("\n".join(lines) if lines else "Історія пуста.")


@dp.callback_query(lambda c: c.data == "secret_button")
async def secret_button(callback: CallbackQuery):
    messages = [
        "😾 Котик незадоволений, що ти натиснув цю кнопку!",
        "🌀 Ти відкрив портал у котячий вимір... але нічого не сталося.",
        "💥 А ти справді думав, що тут щось є?",
        "🐾 Секретів тут нема, тільки хвости.",
    ]
    await callback.message.answer(random.choice(messages))

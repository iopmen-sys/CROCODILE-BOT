import asyncio
import logging
import os
import sqlite3
from datetime import date
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", "crocodile.db")

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

def db():
    return sqlite3.connect(DB_PATH)

def init_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                balance INTEGER NOT NULL DEFAULT 0,
                games_played INTEGER NOT NULL DEFAULT 0,
                joined_at TEXT NOT NULL,
                daily_claim TEXT
            )
        """)

def ensure_user(user):
    with db() as con:
        con.execute("""
            INSERT INTO users(user_id, username, full_name, joined_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              username=excluded.username,
              full_name=excluded.full_name
        """, (user.id, user.username, user.full_name, date.today().isoformat()))

def get_user(user_id):
    with db() as con:
        return con.execute(
            "SELECT user_id, username, full_name, balance, games_played, joined_at, daily_claim FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()

def add_balance(user_id, amount):
    with db() as con:
        con.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))

def add_game(user_id):
    with db() as con:
        con.execute("UPDATE users SET games_played=games_played+1 WHERE user_id=?", (user_id,))

def main_keyboard():
    b = ReplyKeyboardBuilder()
    for label in ["🎮 Игры", "👤 Профиль", "💳 Финансы", "🏆 Лидерборд", "🎁 Подарки", "⚙️ Настройки"]:
        b.add(KeyboardButton(text=label))
    b.adjust(2, 2, 2)
    return b.as_markup(resize_keyboard=True)

def back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Главное меню")]],
        resize_keyboard=True
    )

@dp.message(CommandStart())
async def start(message: Message):
    ensure_user(message.from_user)
    await message.answer(
        f"🐊 Добро пожаловать, {message.from_user.first_name}, в CROCODILE BOT!\n\n"
        "Твоя игровая валюта — 🐊 CROCODILE.\n"
        "Выбирай раздел в меню ниже.",
        reply_markup=main_keyboard()
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "Команды:\n/start — открыть бота\n/help — помощь\n\n"
        "CROCODILE — внутренняя игровая валюта без денежной стоимости."
    )

@dp.message(F.text == "👤 Профиль")
async def profile(message: Message):
    ensure_user(message.from_user)
    u = get_user(message.from_user.id)
    await message.answer(
        "👤 ТВОЙ ПРОФИЛЬ\n\n"
        f"Имя: {u[2]}\n"
        f"ID: {u[0]}\n"
        f"Баланс: 🐊 {u[3]} CROCODILE\n"
        f"Игр сыграно: {u[4]}\n"
        f"В боте с: {u[5]}",
        reply_markup=back_keyboard()
    )

@dp.message(F.text == "🎮 Игры")
async def games(message: Message):
    ensure_user(message.from_user)
    await message.answer(
        "🎮 ИГРЫ\n\n"
        "🎲 Испытай удачу — напиши /roll\n"
        "За победу можно получить 5 CROCODILE.\n"
        "Игра бесплатная, без ставок.",
        reply_markup=back_keyboard()
    )

@dp.message(Command("roll"))
async def roll(message: Message, bot: Bot):
    ensure_user(message.from_user)
    dice = await bot.send_dice(message.chat.id, emoji="🎲")
    value = dice.dice.value
    add_game(message.from_user.id)
    if value >= 4:
        add_balance(message.from_user.id, 5)
        await message.answer(f"🐊 Выпало {value}! Победа — +5 CROCODILE.")
    else:
        await message.answer(f"Выпало {value}. В этот раз без награды. Попробуй ещё!")

@dp.message(F.text == "💳 Финансы")
async def finances(message: Message):
    ensure_user(message.from_user)
    u = get_user(message.from_user.id)
    await message.answer(
        f"💳 ФИНАНСЫ\n\nТекущий баланс: 🐊 {u[3]} CROCODILE\n\n"
        "В этой версии доступны только игровые начисления. "
        "Пополнение и вывод реальных денег не подключены.",
        reply_markup=back_keyboard()
    )

@dp.message(F.text == "🏆 Лидерборд")
async def leaderboard(message: Message):
    ensure_user(message.from_user)
    with db() as con:
        rows = con.execute(
            "SELECT full_name, balance FROM users ORDER BY balance DESC LIMIT 10"
        ).fetchall()
    if not rows:
        await message.answer("Пока рейтинга нет.")
        return
    lines = ["🏆 ТОП ИГРОКОВ\n"]
    for i, (name, balance) in enumerate(rows, 1):
        lines.append(f"{i}. {name} — 🐊 {balance}")
    await message.answer("\n".join(lines), reply_markup=back_keyboard())

@dp.message(F.text == "🎁 Подарки")
async def gifts(message: Message):
    await message.answer(
        "🎁 ПОДАРКИ\n\nСкоро здесь появятся ежедневные бонусы и подарки.",
        reply_markup=back_keyboard()
    )

@dp.message(F.text == "⚙️ Настройки")
async def settings(message: Message):
    await message.answer(
        "⚙️ НАСТРОЙКИ\n\nПока доступны стандартные настройки Telegram.",
        reply_markup=back_keyboard()
    )

@dp.message(F.text == "⬅️ Главное меню")
async def back(message: Message):
    await message.answer("Главное меню 🐊", reply_markup=main_keyboard())

@dp.message()
async def fallback(message: Message):
    await message.answer("Не понял команду. Нажми кнопку меню или отправь /help.")

async def main():
    if not TOKEN:
        raise RuntimeError("Не найден BOT_TOKEN. Создай файл .env по примеру .env.example.")
    init_db()
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

# bot.py
import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, BusinessConnection, BusinessMessagesDeleted
from aiogram.client.default import DefaultBotProperties

# ========== НАСТРОЙКИ ==========
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = 8371473442 # ВСТАВЬ СВОЙ TELEGRAM ID

# ========== ЛОГГИРОВАНИЕ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('messages.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            text TEXT,
            date TIMESTAMP,
            UNIQUE(chat_id, message_id)
        )
    ''')
    conn.commit()
    conn.close()

def save_message(chat_id: str, message_id: int, text: str):
    conn = sqlite3.connect('messages.db')
    cur = conn.cursor()
    cur.execute(
        'INSERT OR REPLACE INTO messages (chat_id, message_id, text, date) VALUES (?, ?, ?, ?)',
        (chat_id, message_id, text, datetime.now())
    )
    conn.commit()
    conn.close()

def get_message(chat_id: str, message_id: int):
    conn = sqlite3.connect('messages.db')
    cur = conn.cursor()
    cur.execute('SELECT text FROM messages WHERE chat_id = ? AND message_id = ?', (chat_id, message_id))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None

def delete_message(chat_id: str, message_id: int):
    conn = sqlite3.connect('messages.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM messages WHERE chat_id = ? AND message_id = ?', (chat_id, message_id))
    conn.commit()
    conn.close()

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ========== BUSINESS ХЕНДЛЕРЫ ==========
@dp.business_connection()
async def on_business_connection(connection: BusinessConnection):
    logger.info(f"Business подключение: {connection.connection_id}")
    await bot.send_message(
        ADMIN_ID,
        f"🔗 <b>Business подключение установлено!</b>\n"
        f"ID: {connection.connection_id}\n"
        f"Чат: {connection.user_id}"
    )

@dp.business_message()
async def handle_business_message(message: types.Message):
    """Сохраняет все сообщения из бизнес-чатов"""
    if not message.business_connection_id:
        return
    
    chat_id = str(message.chat.id)
    msg_id = message.message_id
    text = message.text or message.caption or "[НЕ ТЕКСТОВОЕ СООБЩЕНИЕ]"
    
    save_message(chat_id, msg_id, text)
    logger.info(f"Сохранено: {chat_id} | {msg_id} | {text[:50]}")

@dp.business_messages_deleted()
async def handle_deleted_messages(deleted: BusinessMessagesDeleted):
    """Обработка удалённых сообщений"""
    chat_id = str(deleted.chat.id)
    
    for msg_id in deleted.message_ids:
        saved_text = get_message(chat_id, msg_id)
        
        if saved_text:
            # Отправляем владельцу
            await bot.send_message(
                ADMIN_ID,
                f"🗑 <b>УДАЛЕНО СООБЩЕНИЕ</b>\n"
                f"Чат: {chat_id}\n"
                f"Текст: {saved_text[:500]}\n"
                f"Message ID: {msg_id}"
            )
            delete_message(chat_id, msg_id)
            logger.info(f"Отправлено удаление: {chat_id} | {msg_id}")
        else:
            logger.warning(f"Сообщение {msg_id} не найдено в БД")

# ========== ОБЫЧНЫЕ КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🤖 <b>Добро пожаловать в BOBMOD!</b>\n\n"
        "Это <b>тестовая версия</b>, предназначенная исключительно для тестеров.\n\n"
        "📌 <b>Как работает:</b>\n"
        "1. Подключи бота в <code>Настройки → Автоматизация чатов</code>\n"
        "2. Бот будет сохранять ВСЕ сообщения из чатов\n"
        "3. Если собеседник удалит сообщение — ты получишь его текст в этот чат\n\n"
        "⚠️ <i>Функция удаления работает только в чатах, где бот подключён через автоматизацию</i>\n\n"
        "🚀 <b>Тестируй!</b>"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Помощь по BOBMOD</b>\n\n"
        "Команды:\n"
        "/start — Приветствие\n"
        "/help — Эта справка\n\n"
        "Сейчас доступна только <b>тестовая версия</b>.\n"
        "Функционал будет расширяться."
    )

@dp.message()
async def echo(message: Message):
    """Заглушка для обычных сообщений"""
    if not message.business_connection_id:
        await message.answer("Используй команду /start")

# ========== ЗАПУСК ==========
async def main():
    init_db()
    logger.info("Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

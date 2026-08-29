import asyncio
import logging
import sqlite3
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, BusinessConnection, BusinessMessagesDeleted
from aiogram.client.default import DefaultBotProperties

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = 8371473442

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def save_message(chat_id, message_id, text):
    conn = sqlite3.connect('messages.db')
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO messages (chat_id, message_id, text, date) VALUES (?, ?, ?, ?)',
                (chat_id, message_id, text, datetime.now()))
    conn.commit()
    conn.close()

def get_message(chat_id, message_id):
    conn = sqlite3.connect('messages.db')
    cur = conn.cursor()
    cur.execute('SELECT text FROM messages WHERE chat_id = ? AND message_id = ?', (chat_id, message_id))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None

def delete_message(chat_id, message_id):
    conn = sqlite3.connect('messages.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM messages WHERE chat_id = ? AND message_id = ?', (chat_id, message_id))
    conn.commit()
    conn.close()

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

@dp.business_connection()
async def on_business_connection(connection: BusinessConnection):
    logger.info(f"Business подключение: {connection.connection_id}")
    await bot.send_message(ADMIN_ID, f"🔗 Business подключение установлено!\nID: {connection.connection_id}")

@dp.message()
async def handle_business_message(message: types.Message):
    if not message.business_connection_id:
        return
    save_message(str(message.chat.id), message.message_id, message.text or "[НЕ ТЕКСТ]")
    logger.info(f"Сохранено: {message.chat.id} | {message.message_id}")

@dp.business_messages_deleted()
async def handle_deleted_messages(deleted: BusinessMessagesDeleted):
    for msg_id in deleted.message_ids:
        text = get_message(str(deleted.chat.id), msg_id)
        if text:
            await bot.send_message(ADMIN_ID, f"🗑 УДАЛЕНО:\n{text[:500]}")
            delete_message(str(deleted.chat.id), msg_id)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🤖 Добро пожаловать в BOBMOD!\nТестовая версия.")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("/start — приветствие\n/help — помощь")

@dp.message()
async def echo(message: Message):
    if not message.business_connection_id:
        await message.answer("Используй /start")

async def main():
    init_db()
    logger.info("🚀 БОТ ЗАПУЩЕН!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

# bobmod.py
import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, BusinessConnection, BusinessMessagesDeleted
from aiogram.enums import ParseMode

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "8817614938:AAGDxSTYBs1drVcROpcFGp0OxfJd55HOHiI"
OWNER_ID = 8371473442
DB_NAME = "bobmod.db"
# ========================

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== РАБОТА С БАЗОЙ ДАННЫХ =====
class Database:
    def __init__(self, db_name=DB_NAME):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()
        logger.info(f"База данных {db_name} готова")
    
    def _create_tables(self):
        """Создание таблиц"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                chat_id INTEGER,
                sender_id INTEGER,
                sender_name TEXT,
                sender_username TEXT,
                text TEXT,
                media_type TEXT,
                media_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN DEFAULT 0,
                is_edited BOOLEAN DEFAULT 0,
                original_text TEXT
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS deleted_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                chat_id INTEGER,
                sender_id INTEGER,
                sender_name TEXT,
                text TEXT,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def save_message(self, message: Message):
        """Сохранить сообщение"""
        # Определяем тип медиа
        media_type = None
        media_file_id = None
        
        if message.photo:
            media_type = "photo"
            media_file_id = message.photo[-1].file_id
        elif message.video:
            media_type = "video"
            media_file_id = message.video.file_id
        elif message.document:
            media_type = "document"
            media_file_id = message.document.file_id
        elif message.audio:
            media_type = "audio"
            media_file_id = message.audio.file_id
        elif message.voice:
            media_type = "voice"
            media_file_id = message.voice.file_id
        elif message.sticker:
            media_type = "sticker"
            media_file_id = message.sticker.file_id
        
        # Проверяем существует ли уже сообщение
        self.cursor.execute(
            "SELECT id FROM messages WHERE message_id = ? AND chat_id = ?",
            (message.message_id, message.chat.id)
        )
        existing = self.cursor.fetchone()
        
        if existing:
            # Обновляем (если отредактировано)
            self.cursor.execute('''
                UPDATE messages 
                SET text = ?, is_edited = 1, original_text = COALESCE(original_text, text)
                WHERE message_id = ? AND chat_id = ?
            ''', (
                message.text or message.caption,
                message.message_id,
                message.chat.id
            ))
            logger.info(f"Сообщение {message.message_id} отредактировано")
        else:
            # Сохраняем новое
            self.cursor.execute('''
                INSERT INTO messages (
                    message_id, chat_id, sender_id, sender_name, sender_username,
                    text, media_type, media_file_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message.message_id,
                message.chat.id,
                message.from_user.id,
                message.from_user.full_name,
                message.from_user.username,
                message.text or message.caption,
                media_type,
                media_file_id
            ))
            logger.info(f"Новое сообщение {message.message_id} сохранено")
        
        self.conn.commit()
    
    def mark_deleted(self, message_id: int, chat_id: int):
        """Отметить сообщение как удаленное"""
        # Получаем данные сообщения
        self.cursor.execute(
            "SELECT sender_id, sender_name, text FROM messages WHERE message_id = ? AND chat_id = ?",
            (message_id, chat_id)
        )
        msg = self.cursor.fetchone()
        
        if msg:
            sender_id, sender_name, text = msg
            
            # Сохраняем в таблицу удаленных
            self.cursor.execute('''
                INSERT INTO deleted_messages (message_id, chat_id, sender_id, sender_name, text)
                VALUES (?, ?, ?, ?, ?)
            ''', (message_id, chat_id, sender_id, sender_name, text))
            
            # Отмечаем как удаленное
            self.cursor.execute(
                "UPDATE messages SET is_deleted = 1 WHERE message_id = ? AND chat_id = ?",
                (message_id, chat_id)
            )
            self.conn.commit()
            
            return sender_id, sender_name, text
        
        return None
    
    def get_stats(self):
        """Получить статистику"""
        self.cursor.execute("SELECT COUNT(*) FROM messages")
        total = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM messages WHERE is_deleted = 1")
        deleted = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM messages WHERE is_edited = 1")
        edited = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM deleted_messages")
        in_trash = self.cursor.fetchone()[0]
        
        return {
            "total": total,
            "deleted": deleted,
            "edited": edited,
            "in_trash": in_trash
        }
    
    def close(self):
        self.conn.close()

# Создаем БД
db = Database()

# ===== ОБРАБОТЧИКИ СООБЩЕНИЙ =====

# Обработчик бизнес-подключения
@dp.business_connection()
async def handle_business_connection(connection: BusinessConnection):
    logger.info(f"Business подключение: {connection.connection_id}")
    await bot.send_message(
        chat_id=OWNER_ID,
        text=f"✅ Бизнес-подключение активно!\nПользователь: {connection.user.full_name}"
    )

# Обработчик всех бизнес-сообщений
@dp.message(F.business_connection_id)
async def handle_business_message(message: Message):
    logger.info(f"Сообщение от {message.from_user.id}: {message.text}")
    
    # Сохраняем в БД
    db.save_message(message)
    
    # Отправляем уведомление владельцу (если не от владельца)
    if message.from_user.id != OWNER_ID:
        sender = message.from_user.full_name
        if message.from_user.username:
            sender += f" (@{message.from_user.username})"
        
        text = message.text or message.caption or "[Медиа]"
        if len(text) > 100:
            text = text[:100] + "..."
        
        await bot.send_message(
            chat_id=OWNER_ID,
            text=f"📩 Новое сообщение\nОт: {sender}\nID: {message.from_user.id}\nТекст: {text}"
        )

# Обработчик удаленных сообщений
@dp.business_messages_deleted()
async def handle_deleted_messages(deleted: BusinessMessagesDeleted):
    logger.info(f"Удалено {len(deleted.message_ids)} сообщений в чате {deleted.chat.id}")
    
    for msg_id in deleted.message_ids:
        msg_data = db.mark_deleted(msg_id, deleted.chat.id)
        
        if msg_data:
            sender_id, sender_name, text = msg_data
            
            await bot.send_message(
                chat_id=OWNER_ID,
                text=f"🗑 Сообщение удалено\n"
                     f"От: {sender_name}\n"
                     f"ID: {sender_id}\n"
                     f"Текст: {text or '[Без текста]'}"
            )

# ===== КОМАНДЫ =====

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔ Доступ запрещен")
        return
    
    await message.answer(
        "🤖 BobMod v1.0\n\n"
        "Бот отслеживает все сообщения в бизнес-чатах.\n"
        "Доступные команды:\n"
        "/stats - статистика\n"
        "/help - помощь"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔ Доступ запрещен")
        return
    
    stats = db.get_stats()
    await message.answer(
        f"📊 Статистика\n\n"
        f"Всего сообщений: {stats['total']}\n"
        f"Удалено: {stats['deleted']}\n"
        f"Отредактировано: {stats['edited']}\n"
        f"В корзине: {stats['in_trash']}"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔ Доступ запрещен")
        return
    
    await message.answer(
        "📖 Помощь\n\n"
        "Бот автоматически:\n"
        "- Сохраняет все сообщения\n"
        "- Отслеживает удаление\n"
        "- Отслеживает редактирование\n\n"
        "Команды:\n"
        "/start - приветствие\n"
        "/stats - статистика\n"
        "/help - эта справка"
    )

# ===== ЗАПУСК =====

async def main():
    logger.info("🚀 Запуск BobMod...")
    
    try:
        await bot.send_message(
            chat_id=OWNER_ID,
            text="🤖 BobMod запущен!"
        )
    except:
        logger.warning("Не удалось отправить сообщение владельцу")
    
    try:
        await dp.start_polling(bot)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())

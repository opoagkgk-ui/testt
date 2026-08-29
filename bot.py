# bobmod.py
import asyncio
import logging
import sqlite3
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, BusinessConnection, BusinessMessagesDeleted
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ===== КОНФИГУРАЦИЯ (прямо в коде) =====
BOT_TOKEN = "8817614938:AAGDxSTYBs1drVcROpcFGp0OxfJd55HOHiI"  # Тестовый токен
OWNER_ID = 8371473442  # ID владельца
DB_NAME = "bobmod.db"  # Имя файла базы данных
# ========================================

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Инициализация базы данных
class Database:
    def __init__(self, db_name=DB_NAME):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.init_db()
        logger.info(f"База данных инициализирована: {db_name}")
    
    def init_db(self):
        """Создание таблиц если их нет"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                chat_id INTEGER,
                chat_type TEXT,
                chat_title TEXT,
                sender_id INTEGER,
                sender_name TEXT,
                sender_username TEXT,
                text TEXT,
                media_type TEXT,
                media_file_id TEXT,
                media_caption TEXT,
                date TIMESTAMP,
                is_deleted BOOLEAN DEFAULT 0,
                is_edited BOOLEAN DEFAULT 0,
                original_text TEXT,
                business_connection_id TEXT
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS deleted_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                chat_id INTEGER,
                sender_id INTEGER,
                sender_name TEXT,
                text TEXT,
                deleted_at TIMESTAMP,
                chat_link TEXT
            )
        """)
        
        self.conn.commit()
    
    def save_message(self, message: Message, business_connection_id: str = None):
        """Сохранение сообщения в БД"""
        media_type = None
        media_file_id = None
        media_caption = None
        
        # Определение типа медиа
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
        elif message.animation:
            media_type = "animation"
            media_file_id = message.animation.file_id
        elif message.video_note:
            media_type = "video_note"
            media_file_id = message.video_note.file_id
        
        if message.caption:
            media_caption = message.caption
        
        chat_title = None
        if message.chat.type in ["group", "supergroup"]:
            chat_title = message.chat.title
        elif message.chat.type == "private":
            chat_title = f"Private with {message.from_user.full_name}"
        
        # Проверяем, существует ли уже сообщение
        self.cursor.execute(
            "SELECT id FROM messages WHERE message_id = ? AND chat_id = ?",
            (message.message_id, message.chat.id)
        )
        existing = self.cursor.fetchone()
        
        if existing:
            # Обновляем существующее сообщение (если отредактировано)
            self.cursor.execute("""
                UPDATE messages 
                SET text = ?, media_caption = ?, is_edited = 1, 
                    original_text = COALESCE(original_text, text)
                WHERE message_id = ? AND chat_id = ?
            """, (
                message.text or message.caption,
                media_caption,
                message.message_id,
                message.chat.id
            ))
            logger.info(f"Сообщение {message.message_id} обновлено (редактировано)")
        else:
            # Вставляем новое сообщение
            self.cursor.execute("""
                INSERT INTO messages (
                    message_id, chat_id, chat_type, chat_title,
                    sender_id, sender_name, sender_username,
                    text, media_type, media_file_id, media_caption,
                    date, business_connection_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.message_id,
                message.chat.id,
                message.chat.type,
                chat_title,
                message.from_user.id,
                message.from_user.full_name,
                message.from_user.username,
                message.text or message.caption,
                media_type,
                media_file_id,
                media_caption,
                datetime.now(),
                business_connection_id
            ))
            logger.info(f"Новое сообщение {message.message_id} сохранено")
        
        self.conn.commit()
    
    def mark_as_deleted(self, message_id: int, chat_id: int):
        """Отметка сообщения как удаленного"""
        # Получаем информацию о сообщении перед удалением
        self.cursor.execute(
            """SELECT sender_id, sender_name, text, chat_type, chat_title 
               FROM messages WHERE message_id = ? AND chat_id = ?""",
            (message_id, chat_id)
        )
        msg_data = self.cursor.fetchone()
        
        if msg_data:
            sender_id, sender_name, text, chat_type, chat_title = msg_data
            
            # Сохраняем в таблицу удаленных
            if chat_type == "private":
                chat_link = f"tg://user?id={chat_id}"
            else:
                chat_link = f"tg://openmessage?user_id={sender_id}&chat_id={chat_id}&message_id={message_id}"
            
            self.cursor.execute("""
                INSERT INTO deleted_messages (
                    message_id, chat_id, sender_id, sender_name, text, deleted_at, chat_link
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                message_id, chat_id, sender_id, sender_name, text, datetime.now(), chat_link
            ))
            
            # Отмечаем как удаленное в основной таблице
            self.cursor.execute(
                "UPDATE messages SET is_deleted = 1 WHERE message_id = ? AND chat_id = ?",
                (message_id, chat_id)
            )
            self.conn.commit()
            
            logger.info(f"Сообщение {message_id} отмечено как удаленное")
            return (sender_id, sender_name, text, chat_type, chat_title)
        
        self.conn.commit()
        return None
    
    def get_stats(self):
        """Получение статистики"""
        self.cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM messages WHERE is_deleted = 1")
        deleted_messages = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM messages WHERE is_edited = 1")
        edited_messages = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM deleted_messages")
        total_deleted = self.cursor.fetchone()[0]
        
        # Получаем количество уникальных чатов
        self.cursor.execute("SELECT COUNT(DISTINCT chat_id) FROM messages")
        unique_chats = self.cursor.fetchone()[0]
        
        return {
            "total_messages": total_messages,
            "deleted_messages": deleted_messages,
            "edited_messages": edited_messages,
            "total_deleted": total_deleted,
            "unique_chats": unique_chats
        }
    
    def close(self):
        self.conn.close()
        logger.info("Соединение с БД закрыто")

# Создаем экземпляр БД
db = Database()

# Обработчик подключения бизнес-аккаунта
@dp.business_connection()
async def business_connection_handler(connection: BusinessConnection):
    logger.info(f"Business connection established: {connection.connection_id}")
    logger.info(f"User: {connection.user.full_name} (ID: {connection.user.id})")
    
    # Отправляем уведомление владельцу
    await bot.send_message(
        chat_id=OWNER_ID,
        text=f"✅ <b>Бизнес-подключение установлено!</b>\n\n"
             f"🔗 ID: <code>{connection.connection_id}</code>\n"
             f"👤 Пользователь: {connection.user.full_name}\n"
             f"🆔 ID: <code>{connection.user.id}</code>\n\n"
             f"🤖 BobMod готов к работе!"
    )

# Обработчик всех сообщений из бизнес-чатов
@dp.message(F.business_connection_id)
async def business_message_handler(message: Message):
    logger.info(f"Business message from {message.from_user.id}: {message.text}")
    
    # Сохраняем сообщение в БД
    db.save_message(message, message.business_connection_id)
    
    # Если сообщение от владельца - не отправляем уведомление
    if message.from_user.id == OWNER_ID:
        return
    
    # Отправляем уведомление владельцу о новом сообщении
    sender_info = f"{message.from_user.full_name}"
    if message.from_user.username:
        sender_info += f" (@{message.from_user.username})"
    
    text_preview = message.text or message.caption or "[Медиа]"
    if len(text_preview) > 100:
        text_preview = text_preview[:100] + "..."
    
    media_info = ""
    if message.photo:
        media_info = "📷 Фото"
    elif message.video:
        media_info = "🎬 Видео"
    elif message.document:
        media_info = "📄 Документ"
    elif message.audio:
        media_info = "🎵 Аудио"
    elif message.voice:
        media_info = "🎤 Голосовое"
    elif message.sticker:
        media_info = "🏷 Стикер"
    elif message.animation:
        media_info = "🎞 GIF"
    
    await bot.send_message(
        chat_id=OWNER_ID,
        text=f"📩 <b>Новое сообщение</b>\n"
             f"👤 От: {sender_info}\n"
             f"🆔 ID: <code>{message.from_user.id}</code>\n"
             f"💬 Чат: <code>{message.chat.id}</code>\n"
             f"{f'📎 {media_info}' if media_info else ''}\n"
             f"📝 Текст: {text_preview}\n"
             f"🔗 <a href='tg://user?id={message.from_user.id}'>Ссылка на профиль</a>"
    )

# Обработчик удаленных сообщений
@dp.business_messages_deleted()
async def business_messages_deleted_handler(deleted: BusinessMessagesDeleted):
    logger.info(f"Messages deleted in chat {deleted.chat.id}: {len(deleted.message_ids)} messages")
    
    for msg_id in deleted.message_ids:
        msg_data = db.mark_as_deleted(msg_id, deleted.chat.id)
        
        if msg_data:
            sender_id, sender_name, text, chat_type, chat_title = msg_data
            
            # Отправляем уведомление владельцу
            if chat_type == "private":
                chat_link = f"tg://user?id={deleted.chat.id}"
                chat_info = f"👤 Личный чат"
            else:
                chat_link = f"tg://openmessage?user_id={sender_id}&chat_id={deleted.chat.id}&message_id={msg_id}"
                chat_info = f"👥 Группа: {chat_title or deleted.chat.id}"
            
            await bot.send_message(
                chat_id=OWNER_ID,
                text=f"🗑 <b>Сообщение удалено</b>\n\n"
                     f"👤 От: {sender_name}\n"
                     f"🆔 ID: <code>{sender_id}</code>\n"
                     f"💬 {chat_info}\n"
                     f"📝 Текст: {text or '[Без текста]'}\n"
                     f"🔗 <a href='{chat_link}'>Ссылка на чат</a>"
            )

# Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔ Этот бот доступен только владельцу.")
        return
    
    await message.answer(
        "🤖 <b>BobMod - тестовая версия</b>\n\n"
        "Бот отслеживает все личные чаты и сохраняет сообщения.\n"
        "Доступные команды:\n"
        "📊 /stats - статистика работы\n"
        "❓ /help - помощь\n\n"
        "Для работы требуется Business API подключение."
    )

# Обработчик команды /stats
@dp.message(Command("stats"))
async def stats_command(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔ Доступ запрещен.")
        return
    
    stats = db.get_stats()
    
    await message.answer(
        f"📊 <b>Статистика BobMod</b>\n\n"
        f"📨 Всего сообщений: {stats['total_messages']}\n"
        f"🗑 Удалено: {stats['deleted_messages']}\n"
        f"✏️ Отредактировано: {stats['edited_messages']}\n"
        f"💾 В корзине: {stats['total_deleted']}\n"
        f"💬 Уникальных чатов: {stats['unique_chats']}\n\n"
        f"🕒 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
    )

# Обработчик команды /help
@dp.message(Command("help"))
async def help_command(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔ Доступ запрещен.")
        return
    
    await message.answer(
        "📖 <b>Помощь по BobMod</b>\n\n"
        "<b>Бот автоматически:</b>\n"
        "✅ Сохраняет все сообщения из бизнес-чатов\n"
        "✅ Отслеживает удаление и редактирование\n"
        "✅ Уведомляет о важных событиях\n\n"
        "<b>Команды:</b>\n"
        "/start - приветствие\n"
        "/stats - статистика\n"
        "/help - эта справка\n\n"
        "<b>Информация:</b>\n"
        f"👤 Владелец: <code>{OWNER_ID}</code>\n"
        f"🤖 Версия: 1.0 (тестовая)"
    )

# Обработчик всех остальных сообщений (для отладки)
@dp.message()
async def echo_message(message: Message):
    if message.from_user.id == OWNER_ID:
        logger.info(f"Test message from owner: {message.text}")
        await message.answer("🤖 Бот работает! Используйте /help для списка команд.")

# Обработчик ошибок
@dp.errors()
async def errors_handler(update: types.Update, exception: Exception):
    logger.error(f"Error: {exception}")
    try:
        await bot.send_message(
            chat_id=OWNER_ID,
            text=f"⚠️ <b>Ошибка в боте:</b>\n\n<code>{str(exception)}</code>"
        )
    except:
        pass

# Главная функция
async def main():
    logger.info("🚀 Запуск BobMod...")
    logger.info(f"👤 Владелец: {OWNER_ID}")
    logger.info(f"🤖 Токен: {BOT_TOKEN[:20]}...")
    
    # Отправляем уведомление о запуске
    try:
        await bot.send_message(
            chat_id=OWNER_ID,
            text="🤖 <b>BobMod запущен!</b>\n\n"
                 "Ожидаю бизнес-подключения...\n"
                 f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение владельцу: {e}")
    
    try:
        await dp.start_polling(bot)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())

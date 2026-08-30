import asyncio
import logging
import sqlite3
import html

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message,
    BusinessConnection,
    BusinessMessagesDeleted,
)


# =========================================================
# bobmod TEST — настройки
# =========================================================

BOT_TOKEN = "8817614938:AAGDxSTYBs1drVcROpcFGp0OxfJd55HOHiI"
OWNER_ID = 8371473442

DB_PATH = "bobmod.db"


# =========================================================
# Логирование
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# =========================================================
# База данных
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                connection_id TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,

                sender_id INTEGER,
                sender_name TEXT,

                text TEXT,
                caption TEXT,

                media_type TEXT,
                media_file_id TEXT,

                created_at TEXT,

                edited INTEGER DEFAULT 0,
                deleted INTEGER DEFAULT 0,

                PRIMARY KEY (
                    connection_id,
                    chat_id,
                    message_id
                )
            )
        """)


def save_message(
    connection_id,
    chat_id,
    message_id,
    sender_id,
    sender_name,
    text,
    caption,
    media_type,
    media_file_id,
    created_at
):
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO messages (
                connection_id,
                chat_id,
                message_id,
                sender_id,
                sender_name,
                text,
                caption,
                media_type,
                media_file_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            connection_id,
            chat_id,
            message_id,
            sender_id,
            sender_name,
            text,
            caption,
            media_type,
            media_file_id,
            created_at
        ))


def get_message(connection_id, chat_id, message_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT *
            FROM messages
            WHERE connection_id = ?
              AND chat_id = ?
              AND message_id = ?
        """, (
            connection_id,
            chat_id,
            message_id
        )).fetchone()


def mark_edited(connection_id, chat_id, message_id):
    with get_connection() as conn:
        conn.execute("""
            UPDATE messages
            SET edited = 1
            WHERE connection_id = ?
              AND chat_id = ?
              AND message_id = ?
        """, (
            connection_id,
            chat_id,
            message_id
        ))


def mark_deleted(connection_id, chat_id, message_id):
    with get_connection() as conn:
        conn.execute("""
            UPDATE messages
            SET deleted = 1
            WHERE connection_id = ?
              AND chat_id = ?
              AND message_id = ?
        """, (
            connection_id,
            chat_id,
            message_id
        ))


def get_stats():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(edited), 0) AS edited,
                COALESCE(SUM(deleted), 0) AS deleted
            FROM messages
        """).fetchone()

        return {
            "total": row["total"],
            "edited": row["edited"],
            "deleted": row["deleted"]
        }


# =========================================================
# Вспомогательные функции
# =========================================================

def get_sender(message: Message):
    if message.from_user:
        name_parts = [
            message.from_user.first_name,
            message.from_user.last_name
        ]

        sender_name = " ".join(
            part for part in name_parts if part
        )

        return (
            message.from_user.id,
            sender_name or "Неизвестный"
        )

    return None, "Неизвестный"


def get_media(message: Message):
    if message.photo:
        return "photo", message.photo[-1].file_id

    if message.video:
        return "video", message.video.file_id

    if message.document:
        return "document", message.document.file_id

    if message.audio:
        return "audio", message.audio.file_id

    if message.voice:
        return "voice", message.voice.file_id

    if message.animation:
        return "animation", message.animation.file_id

    if message.sticker:
        return "sticker", message.sticker.file_id

    return None, None


def get_original_content(row):
    if row["text"]:
        return row["text"]

    if row["caption"]:
        return row["caption"]

    if row["media_type"]:
        return f"[Медиа: {row['media_type']}]"

    return "[Сообщение без текста]"


async def send_alert(
    bot: Bot,
    title: str,
    row,
    chat_id: int,
    message_id: int
):
    sender_name = html.escape(
        str(row["sender_name"] or "Неизвестный")
    )

    sender_id = row["sender_id"] or "Неизвестен"

    original_content = html.escape(
        get_original_content(row)
    )

    # tg:// ссылка подходит для попытки открытия сообщения
    chat_link = (
        f"tg://openmessage"
        f"?chat_id={chat_id}"
        f"&message_id={message_id}"
    )

    text = (
        f"<b>{title}</b>\n\n"
        f"<b>Отправитель:</b> {sender_name}\n"
        f"<b>ID:</b> <code>{sender_id}</code>\n\n"
        f"<b>Исходное содержимое:</b>\n"
        f"<blockquote>{original_content}</blockquote>\n\n"
        f'<a href="{chat_link}">Открыть чат</a>'
    )

    await bot.send_message(
        chat_id=OWNER_ID,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )


# =========================================================
# Bot / Dispatcher
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# Команда /start
# =========================================================

@dp.message(Command("start"))
async def command_start(message: Message):
    if message.from_user.id != OWNER_ID:
        return

    await message.answer(
        "🤖 <b>bobmod TEST</b>\n\n"
        "Тестовая версия Business-бота.\n\n"
        "Функции:\n"
        "• сохранение сообщений\n"
        "• сохранение медиа file_id\n"
        "• уведомление при редактировании\n"
        "• уведомление при удалении\n\n"
        "Команды:\n"
        "/start — информация\n"
        "/stats — статистика",
        parse_mode="HTML"
    )


# =========================================================
# Команда /stats
# =========================================================

@dp.message(Command("stats"))
async def command_stats(message: Message):
    if message.from_user.id != OWNER_ID:
        return

    stats = get_stats()

    await message.answer(
        "📊 <b>bobmod TEST — статистика</b>\n\n"
        f"💬 Сохранено сообщений: <b>{stats['total']}</b>\n"
        f"✏️ Отредактировано: <b>{stats['edited']}</b>\n"
        f"🗑 Удалено: <b>{stats['deleted']}</b>",
        parse_mode="HTML"
    )


# =========================================================
# Подключение Telegram Business
# =========================================================

@dp.business_connection()
async def business_connection_handler(
    connection: BusinessConnection
):
    logging.info(
        "Business connection | ID=%s | User=%s | Enabled=%s",
        connection.id,
        connection.user.id,
        connection.is_enabled
    )

    # Дополнительно можно уведомить владельца
    if connection.user.id == OWNER_ID:

        status = (
            "подключена ✅"
            if connection.is_enabled
            else "отключена ❌"
        )

        await bot.send_message(
            OWNER_ID,
            f"🤖 bobmod TEST\n\n"
            f"Business-автоматизация {status}"
        )


# =========================================================
# Новое Business-сообщение
# =========================================================

@dp.business_message()
async def business_message_handler(message: Message):

    # Только личные чаты
    if message.chat.type != "private":
        return

    connection_id = message.business_connection_id

    if not connection_id:
        return

    sender_id, sender_name = get_sender(message)

    media_type, media_file_id = get_media(message)

    save_message(
        connection_id=connection_id,
        chat_id=message.chat.id,
        message_id=message.message_id,

        sender_id=sender_id,
        sender_name=sender_name,

        text=message.text,
        caption=message.caption,

        media_type=media_type,
        media_file_id=media_file_id,

        created_at=message.date.isoformat()
    )

    logging.info(
        "Saved message | chat=%s | message=%s",
        message.chat.id,
        message.message_id
    )


# =========================================================
# Редактирование Business-сообщения
# =========================================================

@dp.edited_business_message()
async def edited_business_message_handler(
    message: Message
):

    if message.chat.type != "private":
        return

    connection_id = message.business_connection_id

    if not connection_id:
        return

    # Получаем исходную версию,
    # сохранённую при первом получении сообщения
    row = get_message(
        connection_id=connection_id,
        chat_id=message.chat.id,
        message_id=message.message_id
    )

    if not row:
        return

    await send_alert(
        bot=bot,
        title="✏️ Сообщение было отредактировано",
        row=row,
        chat_id=message.chat.id,
        message_id=message.message_id
    )

    mark_edited(
        connection_id,
        message.chat.id,
        message.message_id
    )

    logging.info(
        "Edited message | chat=%s | message=%s",
        message.chat.id,
        message.message_id
    )


# =========================================================
# Удаление Business-сообщений
# =========================================================

@dp.deleted_business_messages()
async def deleted_business_messages_handler(
    deleted: BusinessMessagesDeleted
):

    # Только личные чаты
    if deleted.chat.type != "private":
        return

    connection_id = deleted.business_connection_id
    chat_id = deleted.chat.id

    for message_id in deleted.message_ids:

        # Ищем сохранённую исходную версию
        row = get_message(
            connection_id=connection_id,
            chat_id=chat_id,
            message_id=message_id
        )

        # Если бот не успел увидеть сообщение,
        # восстановить его содержимое невозможно
        if not row:
            logging.warning(
                "Deleted message not found in DB | "
                "chat=%s | message=%s",
                chat_id,
                message_id
            )
            continue

        await send_alert(
            bot=bot,
            title="🗑 Сообщение было удалено",
            row=row,
            chat_id=chat_id,
            message_id=message_id
        )

        mark_deleted(
            connection_id,
            chat_id,
            message_id
        )

        logging.info(
            "Deleted message | chat=%s | message=%s",
            chat_id,
            message_id
        )


# =========================================================
# Запуск
# =========================================================

async def main():
    init_db()

    logging.info("Starting bobmod TEST...")

    await dp.start_polling(
        bot,
        allowed_updates=[
            "message",
            "business_connection",
            "business_message",
            "edited_business_message",
            "deleted_business_messages"
        ]
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("bobmod TEST stopped")

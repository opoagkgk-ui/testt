import asyncio
import html
import logging
import sqlite3

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message,
    BusinessConnection,
    BusinessMessagesDeleted,
    MessageEntity,
)


# =========================================================
# bobmod TEST v0.1
# =========================================================

BOT_TOKEN = "8817614938:AAGDxSTYBs1drVcROpcFGp0OxfJd55HOHiI"
OWNER_ID = 8371473442

DB_PATH = "bobmod.db"


# =========================================================
# Custom Emoji
# =========================================================

CUSTOM_EMOJI = {
    "ping": "5444921463536641665",
    "user": "5445223416917422632",
    "id": "5445094086862205639",
    "username": "5445354937405958522",
    "stats": "5444858026869679390",
    "messages": "5445354937405958522",
    "edited": "5447635509205559163",
    "deleted": "5445265116754897405",
    "success": "5445324421663320898",
    "error": "5445267294303314527",
}


# Обычные emoji-якоря.
# Telegram заменит их на соответствующие Custom Emoji.
EMOJI_ANCHORS = {
    "ping": "🏓",
    "user": "👤",
    "id": "🆔",
    "username": "🔗",
    "stats": "📊",
    "messages": "💬",
    "edited": "✏️",
    "deleted": "🗑️",
    "success": "✅",
    "error": "❌",
}


# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# =========================================================
# Bot
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# Database
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS business_connections (
                connection_id TEXT PRIMARY KEY,
                owner_id INTEGER NOT NULL,
                is_enabled INTEGER NOT NULL DEFAULT 1
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                connection_id TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,

                sender_id INTEGER,
                sender_name TEXT,
                sender_username TEXT,

                text TEXT,
                caption TEXT,

                media_type TEXT,
                media_file_id TEXT,

                created_at TEXT,

                edited INTEGER NOT NULL DEFAULT 0,
                deleted INTEGER NOT NULL DEFAULT 0,

                PRIMARY KEY (
                    connection_id,
                    chat_id,
                    message_id
                )
            )
        """)

        conn.commit()


def save_connection(
    connection_id: str,
    owner_id: int,
    is_enabled: bool
):
    with get_connection() as conn:

        conn.execute("""
            INSERT INTO business_connections (
                connection_id,
                owner_id,
                is_enabled
            )
            VALUES (?, ?, ?)

            ON CONFLICT(connection_id)
            DO UPDATE SET
                owner_id = excluded.owner_id,
                is_enabled = excluded.is_enabled
        """, (
            connection_id,
            owner_id,
            int(is_enabled)
        ))

        conn.commit()


def save_message(
    connection_id: str,
    chat_id: int,
    message_id: int,
    sender_id: int | None,
    sender_name: str | None,
    sender_username: str | None,
    text: str | None,
    caption: str | None,
    media_type: str | None,
    media_file_id: str | None,
    created_at: str
):
    with get_connection() as conn:

        conn.execute("""
            INSERT OR IGNORE INTO messages (
                connection_id,
                chat_id,
                message_id,

                sender_id,
                sender_name,
                sender_username,

                text,
                caption,

                media_type,
                media_file_id,

                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            connection_id,
            chat_id,
            message_id,

            sender_id,
            sender_name,
            sender_username,

            text,
            caption,

            media_type,
            media_file_id,

            created_at
        ))

        conn.commit()


def get_message(
    connection_id: str,
    chat_id: int,
    message_id: int
):
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


def mark_edited(
    connection_id: str,
    chat_id: int,
    message_id: int
):
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

        conn.commit()


def mark_deleted(
    connection_id: str,
    chat_id: int,
    message_id: int
):
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

        conn.commit()


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
# Custom Emoji formatter
# =========================================================

def make_entities(text: str):
    """
    Находит emoji-якоря в тексте и создаёт MessageEntity
    type='custom_emoji' с соответствующим custom_emoji_id.

    Важно:
    offsets Telegram считаются в UTF-16 code units.
    """

    entities = []

    for key, anchor in EMOJI_ANCHORS.items():

        custom_id = CUSTOM_EMOJI.get(key)

        if not custom_id:
            continue

        start = 0

        while True:

            position = text.find(
                anchor,
                start
            )

            if position == -1:
                break

            # Python index -> UTF-16 offset
            prefix = text[:position]

            offset = len(
                prefix.encode("utf-16-le")
            ) // 2

            length = len(
                anchor.encode("utf-16-le")
            ) // 2

            entities.append(
                MessageEntity(
                    type="custom_emoji",
                    offset=offset,
                    length=length,
                    custom_emoji_id=custom_id
                )
            )

            start = position + len(anchor)

    # Telegram ожидает сущности в порядке расположения
    entities.sort(
        key=lambda entity: entity.offset
    )

    return entities


# =========================================================
# Send message with Custom Emoji
# =========================================================

async def send_custom_message(
    chat_id: int,
    text: str,
    business_connection_id: str | None = None
):
    entities = make_entities(text)

    return await bot.send_message(
        chat_id=chat_id,
        text=text,
        entities=entities,
        business_connection_id=business_connection_id
    )


async def business_reply(
    message: Message,
    text: str
):
    """
    Ответ именно от подключённого Business-аккаунта.
    """

    connection_id = message.business_connection_id

    if not connection_id:
        return

    await send_custom_message(
        chat_id=message.chat.id,
        text=text,
        business_connection_id=connection_id
    )


# =========================================================
# Helpers
# =========================================================

def get_sender(message: Message):

    if not message.from_user:
        return None, "Неизвестно", None

    user = message.from_user

    name = " ".join(
        part
        for part in [
            user.first_name,
            user.last_name
        ]
        if part
    )

    return (
        user.id,
        name or "Неизвестно",
        user.username
    )


def get_media(message: Message):

    if message.photo:
        return (
            "photo",
            message.photo[-1].file_id
        )

    if message.video:
        return (
            "video",
            message.video.file_id
        )

    if message.document:
        return (
            "document",
            message.document.file_id
        )

    if message.audio:
        return (
            "audio",
            message.audio.file_id
        )

    if message.voice:
        return (
            "voice",
            message.voice.file_id
        )

    if message.animation:
        return (
            "animation",
            message.animation.file_id
        )

    if message.sticker:
        return (
            "sticker",
            message.sticker.file_id
        )

    return None, None


# =========================================================
# .help
# =========================================================

async def handle_help(message: Message):

    await business_reply(
        message,
        (
            "🤖 <b>bobmod TEST</b>\n\n"
            "Доступные команды:\n\n"
            "• <code>.help</code> — помощь\n"
            "• <code>.info</code> — информация о пользователе\n"
            "• <code>.ping</code> — проверка работы"
        )
    )


# =========================================================
# .ping
# =========================================================

async def handle_ping(message: Message):

    await business_reply(
        message,
        (
            "🏓 <b>Pong!</b>\n"
            "🤖 bobmod работает"
        )
    )


# =========================================================
# .info
# =========================================================

async def handle_info(message: Message):

    user = message.from_user

    if not user:

        await business_reply(
            message,
            "❌ Не удалось получить информацию о пользователе."
        )

        return

    name = " ".join(
        part
        for part in [
            user.first_name,
            user.last_name
        ]
        if part
    )

    if not name:
        name = "Не указан"

    name = html.escape(name)

    if user.username:
        username = (
            "@"
            + html.escape(user.username)
        )
    else:
        username = "Не указан"

    text = (
        "👤 <b>Информация</b>\n\n"
        "🆔 ID: "
        f"<code>{user.id}</code>\n"
        "👤 Имя: "
        f"{name}\n"
        "🔗 Username: "
        f"{username}"
    )

    await business_reply(
        message,
        text
    )


# =========================================================
# Business Connection
# =========================================================

@dp.business_connection()
async def business_connection_handler(
    connection: BusinessConnection
):

    logging.info(
        "Business connection | "
        "id=%s | owner=%s | enabled=%s",
        connection.id,
        connection.user.id,
        connection.is_enabled
    )

    save_connection(
        connection_id=connection.id,
        owner_id=connection.user.id,
        is_enabled=connection.is_enabled
    )

    if connection.user.id != OWNER_ID:
        return

    if connection.is_enabled:

        await send_custom_message(
            chat_id=OWNER_ID,
            text=(
                "🤖 <b>bobmod TEST</b>\n\n"
                "Business-подключение включено ✅"
            )
        )

    else:

        await send_custom_message(
            chat_id=OWNER_ID,
            text=(
                "🤖 <b>bobmod TEST</b>\n\n"
                "Business-подключение отключено ❌"
            )
        )


# =========================================================
# New Business message
# =========================================================

@dp.business_message()
async def business_message_handler(
    message: Message
):

    # Только личные чаты
    if message.chat.type != "private":
        return

    connection_id = message.business_connection_id

    if not connection_id:
        return

    sender_id, sender_name, sender_username = (
        get_sender(message)
    )

    media_type, media_file_id = (
        get_media(message)
    )

    # Сохраняем оригинал
    save_message(
        connection_id=connection_id,
        chat_id=message.chat.id,
        message_id=message.message_id,

        sender_id=sender_id,
        sender_name=sender_name,
        sender_username=sender_username,

        text=message.text,
        caption=message.caption,

        media_type=media_type,
        media_file_id=media_file_id,

        created_at=message.date.isoformat()
    )

    logging.info(
        "Business message saved | "
        "chat=%s | message=%s",
        message.chat.id,
        message.message_id
    )

    # Команды должны быть текстовыми
    if not message.text:
        return

    command = (
        message.text
        .strip()
        .lower()
    )

    if command == ".help":
        await handle_help(message)

    elif command == ".ping":
        await handle_ping(message)

    elif command == ".info":
        await handle_info(message)


# =========================================================
# Edited Business message
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

    row = get_message(
        connection_id,
        message.chat.id,
        message.message_id
    )

    if not row:
        logging.warning(
            "Original edited message not found | "
            "chat=%s | message=%s",
            message.chat.id,
            message.message_id
        )

        return

    sender_name = html.escape(
        row["sender_name"] or "Неизвестно"
    )

    sender_id = (
        row["sender_id"]
        or "Неизвестно"
    )

    if row["text"]:
        original_text = row["text"]

    elif row["caption"]:
        original_text = row["caption"]

    elif row["media_type"]:
        original_text = (
            f"[Медиа: {row['media_type']}]"
        )

    else:
        original_text = "[Без текста]"

    original_text = html.escape(
        original_text
    )

    alert = (
        "✏️ <b>Сообщение отредактировано</b>\n\n"
        f"Отправитель: {sender_name}\n"
        f"ID: <code>{sender_id}</code>\n\n"
        "Исходный текст:\n"
        f"<blockquote>{original_text}</blockquote>"
    )

    await send_custom_message(
        chat_id=OWNER_ID,
        text=alert
    )

    mark_edited(
        connection_id,
        message.chat.id,
        message.message_id
    )

    logging.info(
        "Edited message | "
        "chat=%s | message=%s",
        message.chat.id,
        message.message_id
    )


# =========================================================
# Deleted Business messages
# =========================================================

@dp.deleted_business_messages()
async def deleted_business_messages_handler(
    deleted: BusinessMessagesDeleted
):

    if deleted.chat.type != "private":
        return

    connection_id = (
        deleted.business_connection_id
    )

    chat_id = deleted.chat.id

    for message_id in deleted.message_ids:

        row = get_message(
            connection_id,
            chat_id,
            message_id
        )

        # Если бот не успел сохранить сообщение,
        # его содержимое восстановить невозможно.
        if not row:

            logging.warning(
                "Deleted message not found | "
                "chat=%s | message=%s",
                chat_id,
                message_id
            )

            continue

        sender_name = html.escape(
            row["sender_name"] or "Неизвестно"
        )

        sender_id = (
            row["sender_id"]
            or "Неизвестно"
        )

        if row["text"]:
            original_text = row["text"]

        elif row["caption"]:
            original_text = row["caption"]

        elif row["media_type"]:
            original_text = (
                f"[Медиа: {row['media_type']}]"
            )

        else:
            original_text = "[Без текста]"

        original_text = html.escape(
            original_text
        )

        alert = (
            "🗑️ <b>Сообщение удалено</b>\n\n"
            f"Отправитель: {sender_name}\n"
            f"ID: <code>{sender_id}</code>\n\n"
            "Исходное содержимое:\n"
            f"<blockquote>{original_text}</blockquote>"
        )

        await send_custom_message(
            chat_id=OWNER_ID,
            text=alert
        )

        mark_deleted(
            connection_id,
            chat_id,
            message_id
        )

        logging.info(
            "Deleted message | "
            "chat=%s | message=%s",
            chat_id,
            message_id
        )


# =========================================================
# /start
# =========================================================

@dp.message(Command("start"))
async def start_handler(
    message: Message
):

    if not message.from_user:
        return

    if message.from_user.id != OWNER_ID:
        return

    await send_custom_message(
        chat_id=OWNER_ID,
        text=(
            "🤖 <b>bobmod TEST v0.1</b>\n\n"
            "Business-бот работает.\n\n"
            "Команды в Business-чатах:\n"
            "• <code>.help</code>\n"
            "• <code>.info</code>\n"
            "• <code>.ping</code>\n\n"
            "Команда <code>/stats</code> показывает "
            "статистику сохранённых сообщений."
        )
    )


# =========================================================
# /stats
# =========================================================

@dp.message(Command("stats"))
async def stats_handler(
    message: Message
):

    if not message.from_user:
        return

    if message.from_user.id != OWNER_ID:
        return

    stats = get_stats()

    await send_custom_message(
        chat_id=OWNER_ID,
        text=(
            "📊 <b>bobmod TEST v0.1</b>\n\n"
            "💬 Сообщений: "
            f"<b>{stats['total']}</b>\n"
            "✏️ Редактировано: "
            f"<b>{stats['edited']}</b>\n"
            "🗑️ Удалено: "
            f"<b>{stats['deleted']}</b>"
        )
    )


# =========================================================
# Main
# =========================================================

async def main():

    init_db()

    logging.info(
        "Starting bobmod TEST v0.1..."
    )

    await dp.start_polling(
        bot,
        allowed_updates=[
            "message",
            "business_connection",
            "business_message",
            "edited_business_message",
            "deleted_business_messages",
        ]
    )


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logging.info(
            "bobmod TEST stopped"
        )

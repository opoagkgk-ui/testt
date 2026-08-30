import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import (
    Message,
    BusinessConnection,
    BusinessMessagesDeleted,
)

from aiogram.utils.formatting import (
    Text,
    Bold,
    Code,
    CustomEmoji,
)


# =========================================================
# bobmod TEST v0.1
# =========================================================

BOT_TOKEN = "8817614938:AAGDxSTYBs1drVcROpcFGp0OxfJd55HOHiI"

OWNER_ID = 8371473442

TESTER_IDS = {
    5158759132,
}

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


# =========================================================
# Обычные emoji-якоря
# =========================================================

EMOJI = {
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
# DATABASE
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
    sender_id,
    sender_name,
    sender_username,
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
            "deleted": row["deleted"],
        }


# =========================================================
# CUSTOM EMOJI HELPERS
# =========================================================

def emoji(key: str):
    """
    Возвращает CustomEmoji с обычным emoji-якорем.

    Например:
    emoji("ping")
    ->
    🏓 + custom_emoji_id
    """

    return CustomEmoji(
        EMOJI[key],
        custom_emoji_id=CUSTOM_EMOJI[key]
    )


# =========================================================
# Отправка форматированного сообщения
# =========================================================

async def send_formatted(
    chat_id: int,
    content: Text,
    business_connection_id: str | None = None
):
    kwargs = content.as_kwargs()

    kwargs["chat_id"] = chat_id

    if business_connection_id:
        kwargs["business_connection_id"] = (
            business_connection_id
        )

    return await bot.send_message(
        **kwargs
    )


# =========================================================
# Форматирование .help
# =========================================================

def build_help():
    return Text(
        emoji("success"),
        " ",
        Bold("bobmod TEST"),
        "\n\n",

        "Доступные команды:\n\n",

        "• ",
        Code(".help"),
        " — помощь\n",

        "• ",
        Code(".info"),
        " — информация о пользователе\n",

        "• ",
        Code(".ping"),
        " — проверка работы",
    )


# =========================================================
# Форматирование .ping
# =========================================================

def build_ping():
    return Text(
        emoji("ping"),
        " ",
        Bold("Pong!"),
        "\n",

        "🤖 bobmod работает",
    )


# =========================================================
# Форматирование .info
# =========================================================

def build_info(message: Message):
    """
    ВАЖНО:

    message.from_user = тот, кто отправил команду.
    message.chat = собеседник Business-аккаунта.

    Поэтому .info показывает именно A.
    """

    chat = message.chat

    name_parts = []

    if chat.first_name:
        name_parts.append(chat.first_name)

    if chat.last_name:
        name_parts.append(chat.last_name)

    name = " ".join(name_parts)

    if not name:
        name = "Не указан"

    username = (
        f"@{chat.username}"
        if chat.username
        else "Не указан"
    )

    return Text(
        emoji("user"),
        " ",
        Bold("Информация"),
        "\n\n",

        emoji("id"),
        " ",
        Bold("ID:"),
        " ",
        Code(str(chat.id)),
        "\n",

        emoji("user"),
        " ",
        Bold("Имя:"),
        " ",
        name,
        "\n",

        emoji("username"),
        " ",
        Bold("Username:"),
        " ",
        username,
    )


# =========================================================
# Форматирование /stats
# =========================================================

def build_stats():
    stats = get_stats()

    return Text(
        emoji("stats"),
        " ",
        Bold("bobmod TEST v0.1"),
        "\n\n",

        emoji("messages"),
        " ",
        Bold("Сообщений:"),
        " ",
        Code(str(stats["total"])),
        "\n",

        emoji("edited"),
        " ",
        Bold("Редактировано:"),
        " ",
        Code(str(stats["edited"])),
        "\n",

        emoji("deleted"),
        " ",
        Bold("Удалено:"),
        " ",
        Code(str(stats["deleted"])),
    )


# =========================================================
# Замена сообщения командой
# =========================================================

async def replace_command_message(
    message: Message,
    content: Text
):
    """
    Основной механизм команд в Business-чате.

    Вариант 1:
    пытаемся изменить само сообщение команды.

    Вариант 2:
    если Telegram не позволяет изменить сообщение,
    отправляем результат от имени Business-аккаунта
    и удаляем исходную команду.
    """

    connection_id = message.business_connection_id

    if not connection_id:
        return

    kwargs = content.as_kwargs()

    # -----------------------------------------------------
    # Если у команды есть inline keyboard,
    # Telegram не позволит редактировать такое
    # Business-сообщение, если оно не было отправлено ботом.
    # -----------------------------------------------------

    has_inline_keyboard = (
        message.reply_markup is not None
    )

    if not has_inline_keyboard:

        try:

            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                business_connection_id=connection_id,
                **kwargs
            )

            logging.info(
                "Command message edited | "
                "chat=%s | message=%s",
                message.chat.id,
                message.message_id
            )

            return

        except TelegramBadRequest as error:

            logging.warning(
                "Could not edit command message: %s",
                error
            )

        except TelegramForbiddenError as error:

            logging.warning(
                "No permission to edit command message: %s",
                error
            )

    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------

    # Отправляем результат от имени Business-аккаунта.
    await send_formatted(
        chat_id=message.chat.id,
        content=content,
        business_connection_id=connection_id
    )

    # Удаляем исходную команду.
    try:

        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=message.message_id,
            business_connection_id=connection_id
        )

        logging.info(
            "Command message deleted after fallback | "
            "chat=%s | message=%s",
            message.chat.id,
            message.message_id
        )

    except TelegramBadRequest as error:

        logging.warning(
            "Could not delete command message: %s",
            error
        )

    except TelegramForbiddenError as error:

        logging.warning(
            "No permission to delete command message: %s",
            error
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

    # Владелец получает уведомление.
    if connection.user.id != OWNER_ID:
        return

    if connection.is_enabled:

        await send_formatted(
            chat_id=OWNER_ID,
            content=Text(
                "🤖 ",
                Bold("bobmod TEST"),
                "\n\n",
                "Business-подключение включено ",
                emoji("success"),
            )
        )

    else:

        await send_formatted(
            chat_id=OWNER_ID,
            content=Text(
                "🤖 ",
                Bold("bobmod TEST"),
                "\n\n",
                "Business-подключение отключено ",
                emoji("error"),
            )
        )


# =========================================================
# BUSINESS MESSAGE
# =========================================================

@dp.business_message()
async def business_message_handler(
    message: Message
):

    # Только личные диалоги.
    if message.chat.type != "private":
        return

    connection_id = message.business_connection_id

    if not connection_id:
        return

    # -----------------------------------------------------
    # Сохраняем сообщение в БД
    # -----------------------------------------------------

    sender_id = None
    sender_name = None
    sender_username = None

    if message.from_user:

        sender_id = message.from_user.id

        sender_name = " ".join(
            part
            for part in [
                message.from_user.first_name,
                message.from_user.last_name,
            ]
            if part
        )

        sender_username = (
            message.from_user.username
        )

    media_type = None
    media_file_id = None

    if message.photo:

        media_type = "photo"
        media_file_id = (
            message.photo[-1].file_id
        )

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

    elif message.animation:

        media_type = "animation"
        media_file_id = message.animation.file_id

    elif message.sticker:

        media_type = "sticker"
        media_file_id = message.sticker.file_id

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

    # -----------------------------------------------------
    # Команды
    # -----------------------------------------------------

    if not message.text:
        return

    command = (
        message.text
        .strip()
        .lower()
    )

    # .help
    if command == ".help":

        await replace_command_message(
            message,
            build_help()
        )

        return

    # .ping
    if command == ".ping":

        await replace_command_message(
            message,
            build_ping()
        )

        return

    # .info
    if command == ".info":

        # Информация именно о собеседнике A,
        # то есть о message.chat.
        await replace_command_message(
            message,
            build_info(message)
        )

        return


# =========================================================
# EDITED BUSINESS MESSAGE
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

    sender_name = (
        row["sender_name"]
        or "Неизвестно"
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

    alert = Text(
        emoji("edited"),
        " ",
        Bold("Сообщение отредактировано"),
        "\n\n",

        Bold("Отправитель:"),
        " ",
        sender_name,
        "\n",

        Bold("ID:"),
        " ",
        Code(str(sender_id)),
        "\n\n",

        Bold("Исходный текст:"),
        "\n",
        original_text,
    )

    await send_formatted(
        chat_id=OWNER_ID,
        content=alert
    )

    mark_edited(
        connection_id,
        message.chat.id,
        message.message_id
    )


# =========================================================
# DELETED BUSINESS MESSAGES
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

        if not row:

            logging.warning(
                "Deleted message not found | "
                "chat=%s | message=%s",
                chat_id,
                message_id
            )

            continue

        sender_name = (
            row["sender_name"]
            or "Неизвестно"
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

        alert = Text(
            emoji("deleted"),
            " ",
            Bold("Сообщение удалено"),
            "\n\n",

            Bold("Отправитель:"),
            " ",
            sender_name,
            "\n",

            Bold("ID:"),
            " ",
            Code(str(sender_id)),
            "\n\n",

            Bold("Исходное содержимое:"),
            "\n",
            original_text,
        )

        await send_formatted(
            chat_id=OWNER_ID,
            content=alert
        )

        mark_deleted(
            connection_id,
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

    user_id = message.from_user.id

    # -----------------------------------------------------
    # OWNER
    # -----------------------------------------------------

    if user_id == OWNER_ID:

        content = Text(
            "🤖 ",
            Bold("bobmod TEST v0.1"),
            "\n\n",

            "Business-бот работает.",
            "\n\n",

            "Команды в Business-чатах:\n",

            "• ",
            Code(".help"),
            "\n",

            "• ",
            Code(".info"),
            "\n",

            "• ",
            Code(".ping"),
            "\n\n",

            "Команда ",
            Code("/stats"),
            " показывает статистику.",
        )

        await send_formatted(
            chat_id=message.chat.id,
            content=content
        )

        return

    # -----------------------------------------------------
    # TESTER
    # -----------------------------------------------------

    if user_id in TESTER_IDS:

        content = Text(
            "🤖 ",
            Bold("bobmod TEST"),
            "\n\n",

            "🧪 ",
            Bold("Тестовый режим активирован."),
            "\n\n",

            "Ты добавлен в список тестеров.\n\n",

            "Доступные команды:\n",

            "• ",
            Code(".help"),
            "\n",

            "• ",
            Code(".info"),
            "\n",

            "• ",
            Code(".ping"),
        )

        await send_formatted(
            chat_id=message.chat.id,
            content=content
        )

        return


# =========================================================
# /stats
# =========================================================

@dp.message(Command("stats"))
async def stats_handler(
    message: Message
):

    if not message.from_user:
        return

    user_id = message.from_user.id

    # Только OWNER.
    if user_id != OWNER_ID:

        # Тестер и остальные пользователи
        # ничего не получают.
        return

    await send_formatted(
        chat_id=message.chat.id,
        content=build_stats()
    )


# =========================================================
# MAIN
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

import asyncio
import json
import logging
import random
import secrets
import sqlite3
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    MessageEntity,
    BusinessConnection,
    BusinessMessagesDeleted,
)

BOT_TOKEN = os.getenv("API_TOKEN")
if not BOT_TOKEN:
    raise ValueError("API_TOKEN environment variable not set")

OWNER_ID = 8371473442

TESTER_IDS = {
    5158759132,
}

BOT_NAME = "bobmod TEST"
BOT_VERSION = "v0.1"
DATABASE_FILE = "bobmod.sqlite3"

CUSTOM_EMOJI = {
    "robot": "5444921463536641665",
    "ping": "5444921463536641665",
    "user": "5445223416917422632",
    "id": "5445094086862205639",
    "link": "5445354937405958522",
    "stats": "5444858026869679390",
    "message": "5445354937405958522",
    "edit": "5447635509205559163",
    "delete": "5445265116754897405",
    "success": "5445324421663320898",
    "error": "5445267294303314527",
}

logging.basicConfig(
    level=logging.INFO,
    format=("%(asctime)s | %(levelname)s | %(name)s | %(message)s"),
)
logger = logging.getLogger("bobmod")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

db = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
db.row_factory = sqlite3.Row

#функция1
def init_database():
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_connections (
            connection_id TEXT PRIMARY KEY,
            owner_id INTEGER NOT NULL,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_id TEXT NOT NULL,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            sender_id INTEGER,
            sender_username TEXT,
            sender_first_name TEXT,
            sender_last_name TEXT,
            sender_name TEXT,
            text TEXT,
            caption TEXT,
            media_type TEXT,
            media_file_id TEXT,
            is_edited INTEGER NOT NULL DEFAULT 0,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (connection_id, chat_id, message_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            connection_id TEXT PRIMARY KEY,
            time_enabled INTEGER NOT NULL DEFAULT 0,
            timezone TEXT NOT NULL DEFAULT 'Europe/Moscow',
            time_format TEXT NOT NULL DEFAULT '%H:%M',
            message_style TEXT NOT NULL DEFAULT 'off',
            profile_base_first_name TEXT,
            profile_base_last_name TEXT,
            last_profile_time TEXT,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            game_type TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            host_id INTEGER NOT NULL,
            guest_id INTEGER NOT NULL,
            state TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT NOT NULL,
            data TEXT,
            updated_at TEXT NOT NULL
        )
    """)
    db.commit()

#функция2
def utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")

#функция3
def generate_game_id() -> str:
    return secrets.token_hex(8)

#функция4
def encode_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)

#функция5
def decode_json(data: str) -> dict:
    try:
        value = json.loads(data)
        if isinstance(value, dict):
            return value
    except Exception:
        pass
    return {}

#функция6
def save_business_connection(connection: BusinessConnection):
    cursor = db.cursor()
    user = connection.user
    cursor.execute("""
        INSERT INTO business_connections (
            connection_id, owner_id, user_id, username, first_name, last_name,
            is_enabled, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(connection_id) DO UPDATE SET
            owner_id = excluded.owner_id,
            user_id = excluded.user_id,
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            is_enabled = 1,
            updated_at = excluded.updated_at
    """, (connection.id, user.id, user.id, user.username, user.first_name, user.last_name, utc_now(), utc_now()))
    cursor.execute("""
        INSERT OR IGNORE INTO settings (connection_id, updated_at) VALUES (?, ?)
    """, (connection.id, utc_now()))
    db.commit()

#функция7
def disable_business_connection(connection_id: str):
    cursor = db.cursor()
    cursor.execute("""
        UPDATE business_connections SET is_enabled = 0, updated_at = ? WHERE connection_id = ?
    """, (utc_now(), connection_id))
    db.commit()

#функция8
def get_business_connection(connection_id: str):
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM business_connections WHERE connection_id = ? AND is_enabled = 1 LIMIT 1
    """, (connection_id,))
    return cursor.fetchone()

#функция9
def get_connection_by_owner(owner_id: int):
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM business_connections WHERE owner_id = ? AND is_enabled = 1 ORDER BY updated_at DESC LIMIT 1
    """, (owner_id,))
    return cursor.fetchone()

#функция10
def get_settings(connection_id: str):
    cursor = db.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO settings (connection_id, updated_at) VALUES (?, ?)
    """, (connection_id, utc_now()))
    db.commit()
    cursor.execute("""
        SELECT * FROM settings WHERE connection_id = ? LIMIT 1
    """, (connection_id,))
    return cursor.fetchone()

#функция11
def update_settings(connection_id: str, **values):
    allowed = {
        "time_enabled", "timezone", "time_format", "message_style",
        "profile_base_first_name", "profile_base_last_name", "last_profile_time"
    }
    filtered = {key: value for key, value in values.items() if key in allowed}
    if not filtered:
        return
    filtered["updated_at"] = utc_now()
    columns = []
    parameters = []
    for key, value in filtered.items():
        columns.append(f"{key} = ?")
        parameters.append(value)
    parameters.append(connection_id)
    cursor = db.cursor()
    cursor.execute(f"UPDATE settings SET {', '.join(columns)} WHERE connection_id = ?", parameters)
    db.commit()

#функция12
def set_user_state(user_id: int, state: str, data: Optional[dict] = None):
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO user_states (user_id, state, data, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            state = excluded.state,
            data = excluded.data,
            updated_at = excluded.updated_at
    """, (user_id, state, encode_json(data or {}), utc_now()))
    db.commit()

#функция13
def get_user_state(user_id: int):
    cursor = db.cursor()
    cursor.execute("SELECT state, data FROM user_states WHERE user_id = ? LIMIT 1", (user_id,))
    row = cursor.fetchone()
    if not row:
        return None, {}
    return row["state"], decode_json(row["data"] or "{}")

#функция14
def clear_user_state(user_id: int):
    cursor = db.cursor()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    db.commit()

#функция15
def save_message(connection_id: str, message: Message):
    sender = message.from_user
    if sender:
        sender_id = sender.id
        sender_username = sender.username
        sender_first_name = sender.first_name
        sender_last_name = sender.last_name
        sender_name = sender.full_name
    else:
        sender_id = None
        sender_username = None
        sender_first_name = None
        sender_last_name = None
        sender_name = "Неизвестно"
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
    elif message.animation:
        media_type = "animation"
        media_file_id = message.animation.file_id
    elif message.audio:
        media_type = "audio"
        media_file_id = message.audio.file_id
    elif message.voice:
        media_type = "voice"
        media_file_id = message.voice.file_id
    elif message.video_note:
        media_type = "video_note"
        media_file_id = message.video_note.file_id
    elif message.sticker:
        media_type = "sticker"
        media_file_id = message.sticker.file_id
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO messages (
            connection_id, chat_id, message_id,
            sender_id, sender_username, sender_first_name, sender_last_name, sender_name,
            text, caption, media_type, media_file_id,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(connection_id, chat_id, message_id) DO UPDATE SET
            sender_id = excluded.sender_id,
            sender_username = excluded.sender_username,
            sender_first_name = excluded.sender_first_name,
            sender_last_name = excluded.sender_last_name,
            sender_name = excluded.sender_name,
            text = excluded.text,
            caption = excluded.caption,
            media_type = excluded.media_type,
            media_file_id = excluded.media_file_id,
            updated_at = excluded.updated_at
    """, (
        connection_id,
        message.chat.id, message.message_id,
        sender_id, sender_username, sender_first_name, sender_last_name, sender_name,
        message.text, message.caption,
        media_type, media_file_id,
        utc_now(), utc_now()
    ))
    db.commit()

#функция16
def get_saved_message(connection_id: str, chat_id: int, message_id: int):
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM messages WHERE connection_id = ? AND chat_id = ? AND message_id = ? LIMIT 1
    """, (connection_id, chat_id, message_id))
    return cursor.fetchone()

#функция17
def mark_message_edited(connection_id: str, chat_id: int, message_id: int):
    cursor = db.cursor()
    cursor.execute("""
        UPDATE messages SET is_edited = 1, updated_at = ? WHERE connection_id = ? AND chat_id = ? AND message_id = ?
    """, (utc_now(), connection_id, chat_id, message_id))
    db.commit()

#функция18
def mark_message_deleted(connection_id: str, chat_id: int, message_id: int):
    cursor = db.cursor()
    cursor.execute("""
        UPDATE messages SET is_deleted = 1, updated_at = ? WHERE connection_id = ? AND chat_id = ? AND message_id = ?
    """, (utc_now(), connection_id, chat_id, message_id))
    db.commit()

#функция19
def save_game(game_id: str, game_type: str, connection_id: str, chat_id: int, message_id: int,
              host_id: int, guest_id: int, state: str, data: dict):
    cursor = db.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO games (
            game_id, game_type, connection_id, chat_id, message_id,
            host_id, guest_id, state, data, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (game_id, game_type, connection_id, chat_id, message_id,
          host_id, guest_id, state, encode_json(data), utc_now(), utc_now()))
    db.commit()

#функция20
def get_game(game_id: str):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM games WHERE game_id = ? LIMIT 1", (game_id,))
    return cursor.fetchone()

#функция21
def update_game(game_id: str, state: Optional[str] = None, data: Optional[dict] = None):
    cursor = db.cursor()
    if state is not None:
        cursor.execute("UPDATE games SET state = ?, updated_at = ? WHERE game_id = ?", (state, utc_now(), game_id))
    if data is not None:
        cursor.execute("UPDATE games SET data = ?, updated_at = ? WHERE game_id = ?", (encode_json(data), utc_now(), game_id))
    db.commit()

#функция22
def delete_game(game_id: str):
    cursor = db.cursor()
    cursor.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
    db.commit()

#функция23
def user_display_name(user) -> str:
    if not user:
        return "Неизвестно"
    if getattr(user, "full_name", None):
        return user.full_name
    if getattr(user, "username", None):
        return "@" + user.username
    return str(user.id)

#функция24
def format_username(username: Optional[str]) -> str:
    if not username:
        return "нет"
    return "@" + username

#функция25
def get_chat_link(message: Message) -> Optional[str]:
    chat = message.chat
    if chat.username:
        return f"https://t.me/{chat.username}"
    return None

#функция26
def custom_emoji_entity(emoji_id: str, offset: int) -> MessageEntity:
    return MessageEntity(type="custom_emoji", offset=offset, length=2, custom_emoji_id=emoji_id)

#функция27
@dp.business_connection()
async def on_business_connection(connection: BusinessConnection):
    try:
        logger.info("Business connection received: %s", connection.id)
        logger.info("Business owner: %s", connection.user.id)
        save_business_connection(connection)
    except Exception:
        logger.exception("Failed to process Business connection")

#функция28
def get_connection_id_from_message(message: Message) -> Optional[str]:
    return getattr(message, "business_connection_id", None)

#функция29
def is_business_message(message: Message) -> bool:
    return bool(get_connection_id_from_message(message))

#функция30
def get_message_sender(message: Message):
    return message.from_user

#функция31
@dp.business_message()
async def on_business_message(message: Message):
    connection_id = get_connection_id_from_message(message)
    if not connection_id:
        return
    connection = get_business_connection(connection_id)
    if not connection:
        logger.warning("Unknown Business connection: %s", connection_id)
        return
    try:
        save_message(connection_id, message)
        logger.info("Business message saved: connection=%s chat=%s message=%s",
                    connection_id, message.chat.id, message.message_id)
        if message.text:
            await process_business_command(message, connection)
    except Exception:
        logger.exception("Error in Business message handler")

#функция32
@dp.edited_business_message()
async def on_edited_business_message(message: Message):
    connection_id = get_connection_id_from_message(message)
    if not connection_id:
        return
    connection = get_business_connection(connection_id)
    if not connection:
        return
    try:
        old_message = get_saved_message(connection_id, message.chat.id, message.message_id)
        save_message(connection_id, message)
        mark_message_edited(connection_id, message.chat.id, message.message_id)
        if not old_message:
            logger.info("Edited message has no saved original: chat=%s message=%s",
                        message.chat.id, message.message_id)
            return
        await notify_message_changed(connection, old_message, message, change_type="edited")
    except Exception:
        logger.exception("Error processing edited Business message")

#функция33
@dp.deleted_business_messages()
async def on_deleted_business_messages(event: BusinessMessagesDeleted):
    connection_id = getattr(event, "business_connection_id", None)
    if not connection_id:
        return
    connection = get_business_connection(connection_id)
    if not connection:
        return
    try:
        for message_id in event.message_ids:
            chat = getattr(event, "chat", None)
            if not chat:
                continue
            chat_id = chat.id
            old_message = get_saved_message(connection_id, chat_id, message_id)
            mark_message_deleted(connection_id, chat_id, message_id)
            if not old_message:
                continue
            await notify_deleted_message(connection, old_message)
    except Exception:
        logger.exception("Error processing deleted Business messages")

#функция34
def get_saved_message_content(row) -> str:
    parts = []
    text = row["text"]
    caption = row["caption"]
    media_type = row["media_type"]
    if text:
        parts.append(text)
    elif caption:
        parts.append(caption)
    if media_type:
        if media_type == "photo":
            parts.append("[Фото]")
        elif media_type == "video":
            parts.append("[Видео]")
        elif media_type == "document":
            parts.append("[Документ]")
        elif media_type == "animation":
            parts.append("[GIF]")
        elif media_type == "audio":
            parts.append("[Аудио]")
        elif media_type == "voice":
            parts.append("[Голосовое сообщение]")
        elif media_type == "video_note":
            parts.append("[Видеосообщение]")
        elif media_type == "sticker":
            parts.append("[Стикер]")
        else:
            parts.append(f"[{media_type}]")
    if not parts:
        return "[Сообщение без текста]"
    return "\n".join(parts)

#функция35
async def get_chat_link_for_notification(chat_id: int, username: Optional[str]) -> Optional[str]:
    if username:
        return f"https://t.me/{username}"
    return None

#функция36
async def notify_message_changed(connection, old_message, new_message: Message, change_type: str):
    owner_id = connection["owner_id"]
    sender_name = old_message["sender_name"] or "Неизвестно"
    sender_id = old_message["sender_id"]
    username = old_message["sender_username"]
    original_text = get_saved_message_content(old_message)
    if change_type == "edited":
        title = "✏️ <b>Сообщение изменено</b>"
    else:
        title = "🗑️ <b>Сообщение изменено</b>"
    chat_link = await get_chat_link_for_notification(new_message.chat.id, new_message.chat.username)
    if username:
        sender_line = f"👤 <b>Отправитель:</b> {escape_html(sender_name)} ({escape_html('@' + username)})"
    else:
        sender_line = f"👤 <b>Отправитель:</b> {escape_html(sender_name)}"
    if sender_id is not None:
        id_line = f"🆔 <b>ID:</b> <code>{sender_id}</code>"
    else:
        id_line = "🆔 <b>ID:</b> неизвестен"
    if chat_link:
        chat_line = f'🔗 <b>Чат:</b> <a href="{chat_link}">открыть</a>'
    else:
        chat_line = "🔗 <b>Чат:</b> прямая ссылка недоступна"
    text = (
        f"{title}\n\n"
        f"{sender_line}\n"
        f"{id_line}\n"
        f"{chat_line}\n\n"
        f"💬 <b>Исходное сообщение:</b>\n"
        f"<blockquote>{escape_html(original_text)}</blockquote>"
    )
    try:
        await bot.send_message(owner_id, text)
    except Exception:
        logger.exception("Could not send edit notification")

#функция37
async def notify_deleted_message(connection, old_message):
    owner_id = connection["owner_id"]
    sender_name = old_message["sender_name"] or "Неизвестно"
    sender_id = old_message["sender_id"]
    username = old_message["sender_username"]
    original_text = get_saved_message_content(old_message)
    if username:
        sender_line = f"👤 <b>Отправитель:</b> {escape_html(sender_name)} ({escape_html('@' + username)})"
    else:
        sender_line = f"👤 <b>Отправитель:</b> {escape_html(sender_name)}"
    if sender_id is not None:
        id_line = f"🆔 <b>ID:</b> <code>{sender_id}</code>"
    else:
        id_line = "🆔 <b>ID:</b> неизвестен"
    chat_link = None
    if old_message["sender_username"]:
        chat_link = f"https://t.me/{old_message['sender_username']}"
    if chat_link:
        chat_line = f'🔗 <b>Чат:</b> <a href="{chat_link}">открыть</a>'
    else:
        chat_line = "🔗 <b>Чат:</b> прямая ссылка недоступна"
    text = (
        "🗑️ <b>Сообщение удалено</b>\n\n"
        f"{sender_line}\n"
        f"{id_line}\n"
        f"{chat_line}\n\n"
        "💬 <b>Сохранённое сообщение:</b>\n"
        f"<blockquote>{escape_html(original_text)}</blockquote>"
    )
    try:
        await bot.send_message(owner_id, text)
    except Exception:
        logger.exception("Could not send deletion notification")

#функция38
def escape_html(value) -> str:
    if value is None:
        return ""
    value = str(value)
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

#функция39
def extract_business_command(text: Optional[str]):
    if not text:
        return None
    text = text.strip()
    if not text.startswith("."):
        return None
    first_word = text.split(maxsplit=1)[0]
    command = first_word.lower()
    supported = {".help", ".info", ".ping", ".dice", ".ttt", ".roulette", ".game"}
    if command not in supported:
        return None
    return command

#функция40
async def process_business_command(message: Message, connection):
    command = extract_business_command(message.text)
    if not command:
        return
    if message.chat.type != "private":
        return
    if command == ".help":
        await command_help(message, connection)
        return
    if command == ".info":
        await command_info(message, connection)
        return
    if command == ".ping":
        await command_ping(message, connection)
        return
    if command == ".dice":
        await command_dice(message, connection)
        return
    if command == ".ttt":
        await command_ttt(message, connection)
        return
    if command == ".roulette":
        await command_roulette(message, connection)
        return
    if command == ".game":
        await command_game(message, connection)
        return

#функция41
async def delete_business_command(message: Message, connection):
    try:
        await bot.delete_business_messages(
            business_connection_id=connection["connection_id"],
            chat_id=message.chat.id,
            message_ids=[message.message_id],
        )
        return True
    except Exception as error:
        logger.warning("Could not delete Business command %s: %s", message.message_id, error)
        return False

#функция42
async def send_business_response(message: Message, connection, text: str, reply_markup=None):
    connection_id = connection["connection_id"]
    sent = None
    try:
        sent = await bot.send_message(
            chat_id=message.chat.id,
            text=text,
            reply_markup=reply_markup,
            business_connection_id=connection_id,
        )
    except Exception as error:
        logger.warning("Business send_message failed: %s", error)
        try:
            sent = await bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=reply_markup,
            )
        except Exception:
            logger.exception("Fallback message failed")
    await delete_business_command(message, connection)
    return sent

#функция43
async def command_help(message: Message, connection):
    text = (
        "🤖 <b>bobmod</b>\n\n"
        "Доступные команды:\n\n"
        "<code>.help</code> — список команд\n"
        "<code>.info</code> — информация о собеседнике\n"
        "<code>.ping</code> — проверка работы бота\n"
        "<code>.game</code> — список игр\n"
        "<code>.dice</code> — игра на чёт/нечёт\n"
        "<code>.ttt</code> — крестики-нолики\n"
        "<code>.roulette</code> — безопасная игра на случайность"
    )
    await send_business_response(message, connection, text)

#функция44
async def command_ping(message: Message, connection):
    text = "🏓 <b>Pong!</b>\n\n🤖 bobmod работает."
    await send_business_response(message, connection, text)

#функция45
async def get_target_user_info(message: Message):
    chat = message.chat
    return chat

#функция46
async def command_info(message: Message, connection):
    target = await get_target_user_info(message)
    if not target:
        await send_business_response(message, connection, "❌ Не удалось определить собеседника.")
        return
    target_id = target.id
    first_name = target.first_name or ""
    last_name = target.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    if not full_name:
        full_name = "Не указано"
    username = target.username
    if username:
        username_text = f"@{username}"
        profile_link = f'<a href="https://t.me/{username}">открыть профиль</a>'
    else:
        username_text = "нет"
        profile_link = "недоступна"
    text = (
        "👤 <b>Информация о пользователе</b>\n\n"
        f"👤 <b>Имя:</b> {escape_html(full_name)}\n"
        f"🆔 <b>ID:</b> <code>{target_id}</code>\n"
        f"👤 <b>Username:</b> {escape_html(username_text)}\n"
        f"🔗 <b>Профиль:</b> {profile_link}"
    )
    await send_business_response(message, connection, text)

#функция47
async def answer_callback_safely(callback: CallbackQuery, text: Optional[str] = None, show_alert: bool = False):
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except Exception:
        pass

#функция48
def is_game_player(game, user_id: int) -> bool:
    return user_id in {game["host_id"], game["guest_id"]}

#функция49
def get_opponent_id(game, user_id: int) -> Optional[int]:
    if user_id == game["host_id"]:
        return game["guest_id"]
    if user_id == game["guest_id"]:
        return game["host_id"]
    return None

#функция50
async def edit_game_message(game, text: str, reply_markup=None):
    connection_id = game["connection_id"]
    try:
        await bot.edit_message_text(
            business_connection_id=connection_id,
            chat_id=game["chat_id"],
            message_id=game["message_id"],
            text=text,
            reply_markup=reply_markup,
        )
        return True
    except Exception as business_error:
        logger.warning("Business game edit failed: %s", business_error)
    try:
        await bot.edit_message_text(
            chat_id=game["chat_id"],
            message_id=game["message_id"],
            text=text,
            reply_markup=reply_markup,
        )
        return True
    except Exception:
        logger.exception("Could not edit game message")
        return False

#функция51
async def send_game_message(message: Message, connection, text: str, reply_markup):
    return await send_business_response(message, connection, text, reply_markup)

#функция52
def dice_host_keyboard(game_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Чётное", callback_data=f"dice:{game_id}:host:even"),
            InlineKeyboardButton(text="Нечётное", callback_data=f"dice:{game_id}:host:odd"),
        ]
    ])

#функция53
def dice_guest_keyboard(game_id: str, forbidden_choice: str) -> InlineKeyboardMarkup:
    buttons = []
    if forbidden_choice != "even":
        buttons.append(InlineKeyboardButton(text="Чётное", callback_data=f"dice:{game_id}:guest:even"))
    if forbidden_choice != "odd":
        buttons.append(InlineKeyboardButton(text="Нечётное", callback_data=f"dice:{game_id}:guest:odd"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

#функция54
async def command_dice(message: Message, connection):
    host = message.from_user
    if not host:
        await send_business_response(message, connection, "❌ Не удалось определить игрока.")
        return
    guest_id = message.chat.id
    if guest_id == host.id:
        await send_business_response(message, connection, "❌ Нужен другой участник.")
        return
    game_id = generate_game_id()
    text = (
        "🎲 <b>Чёт или нечёт</b>\n\n"
        f"Первый игрок: <b>{escape_html(user_display_name(host))}</b>\n\n"
        "Выбери сторону:"
    )
    sent = await send_game_message(message, connection, text, dice_host_keyboard(game_id))
    if not sent:
        return
    save_game(
        game_id=game_id,
        game_type="dice",
        connection_id=connection["connection_id"],
        chat_id=message.chat.id,
        message_id=sent.message_id,
        host_id=host.id,
        guest_id=guest_id,
        state="host_choice",
        data={"host_choice": None, "guest_choice": None},
    )

#функция55
@dp.callback_query(F.data.startswith("dice:"))
async def dice_callback(callback: CallbackQuery):
    if not callback.data:
        return
    parts = callback.data.split(":")
    if len(parts) != 4:
        await answer_callback_safely(callback, "Ошибка данных игры.", True)
        return
    _, game_id, player_type, choice = parts
    game = get_game(game_id)
    if not game:
        await answer_callback_safely(callback, "Игра уже закончена.", True)
        return
    if game["game_type"] != "dice":
        await answer_callback_safely(callback, "Это не игра в кости.", True)
        return
    if not callback.from_user:
        return
    user_id = callback.from_user.id
    data = decode_json(game["data"])
    if player_type == "host":
        if user_id != game["host_id"]:
            await answer_callback_safely(callback, "Этот выбор не для тебя.", True)
            return
        if game["state"] != "host_choice":
            await answer_callback_safely(callback, "Выбор уже сделан.", True)
            return
        if choice not in {"even", "odd"}:
            await answer_callback_safely(callback, "Неверный вариант.", True)
            return
        data["host_choice"] = choice
        update_game(game_id, state="guest_choice", data=data)
        host_choice_text = "чётное" if choice == "even" else "нечётное"
        text = (
            "🎲 <b>Чёт или нечёт</b>\n\n"
            f"Первый игрок выбрал: <b>{host_choice_text}</b>\n\n"
            "Теперь второй игрок выбирает оставшийся вариант."
        )
        await edit_game_message(game, text, dice_guest_keyboard(game_id, choice))
        await answer_callback_safely(callback, "Выбор принят.")
        return
    if player_type == "guest":
        if user_id != game["guest_id"]:
            await answer_callback_safely(callback, "Этот выбор не для тебя.", True)
            return
        if game["state"] != "guest_choice":
            await answer_callback_safely(callback, "Сейчас не твой ход.", True)
            return
        host_choice = data.get("host_choice")
        if choice not in {"even", "odd"}:
            await answer_callback_safely(callback, "Неверный вариант.", True)
            return
        if choice == host_choice:
            await answer_callback_safely(callback, "Этот вариант уже занят.", True)
            return
        data["guest_choice"] = choice
        number = random.randint(1, 6)
        result_type = "even" if number % 2 == 0 else "odd"
        if result_type == host_choice:
            winner_id = game["host_id"]
            winner_type = "Первый игрок"
        else:
            winner_id = game["guest_id"]
            winner_type = "Второй игрок"
        host_text = "чётное" if host_choice == "even" else "нечётное"
        guest_text = "чётное" if choice == "even" else "нечётное"
        result_text = "чётное" if result_type == "even" else "нечётное"
        text = (
            "🎲 <b>Чёт или нечёт</b>\n\n"
            f"Первый игрок: <b>{host_text}</b>\n"
            f"Второй игрок: <b>{guest_text}</b>\n\n"
            f"Выпало число: <b>{number}</b>\n"
            f"Результат: <b>{result_text}</b>\n\n"
            f"🏆 Победитель: <b>{winner_type}</b>"
        )
        data["number"] = number
        data["winner_id"] = winner_id
        update_game(game_id, state="finished", data=data)
        await edit_game_message(game, text, None)
        await answer_callback_safely(callback, "Игра завершена.")

#функция56
TTT_EMPTY = " "
TTT_HOST_SYMBOL = "X"
TTT_GUEST_SYMBOL = "O"

#функция57
def create_ttt_board():
    return [TTT_EMPTY] * 9

#функция58
def ttt_button_text(value: str) -> str:
    if value == TTT_HOST_SYMBOL:
        return "❌"
    if value == TTT_GUEST_SYMBOL:
        return "⭕"
    return "·"

#функция59
def ttt_keyboard(game_id: str, board: list) -> InlineKeyboardMarkup:
    rows = []
    for row in range(3):
        buttons = []
        for column in range(3):
            position = row * 3 + column
            buttons.append(InlineKeyboardButton(
                text=ttt_button_text(board[position]),
                callback_data=f"ttt:{game_id}:{position}"
            ))
        rows.append(buttons)
    return InlineKeyboardMarkup(inline_keyboard=rows)

#функция60
def ttt_get_winner(board: list) -> Optional[str]:
    winning_lines = [
        (0,1,2), (3,4,5), (6,7,8),
        (0,3,6), (1,4,7), (2,5,8),
        (0,4,8), (2,4,6)
    ]
    for a,b,c in winning_lines:
        if board[a] != TTT_EMPTY and board[a] == board[b] and board[b] == board[c]:
            return board[a]
    return None

#функция61
def ttt_is_draw(board: list) -> bool:
    return all(cell != TTT_EMPTY for cell in board)

#функция62
def ttt_player_name(game, symbol: str) -> str:
    if symbol == TTT_HOST_SYMBOL:
        return "Крестики ❌"
    return "Нолики ⭕"

#функция63
def ttt_game_text(game, current_symbol: str) -> str:
    return (
        "🎮 <b>Крестики-нолики</b>\n\n"
        "Первый игрок — ❌\n"
        "Второй игрок — ⭕\n\n"
        f"Ход: <b>{ttt_player_name(game, current_symbol)}</b>"
    )

#функция64
async def command_ttt(message: Message, connection):
    host = message.from_user
    if not host:
        await send_business_response(message, connection, "❌ Не удалось определить первого игрока.")
        return
    guest_id = message.chat.id
    if guest_id == host.id:
        await send_business_response(message, connection, "❌ Нужен другой игрок.")
        return
    game_id = generate_game_id()
    board = create_ttt_board()
    text = (
        "🎮 <b>Крестики-нолики</b>\n\n"
        "Первый игрок — ❌\n"
        "Второй игрок — ⭕\n\n"
        "Ход: <b>Крестики ❌</b>"
    )
    sent = await send_game_message(message, connection, text, ttt_keyboard(game_id, board))
    if not sent:
        return
    save_game(
        game_id=game_id,
        game_type="ttt",
        connection_id=connection["connection_id"],
        chat_id=message.chat.id,
        message_id=sent.message_id,
        host_id=host.id,
        guest_id=guest_id,
        state="playing",
        data={"board": board, "current_symbol": TTT_HOST_SYMBOL},
    )

#функция65
@dp.callback_query(F.data.startswith("ttt:"))
async def ttt_callback(callback: CallbackQuery):
    if not callback.data:
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await answer_callback_safely(callback, "Ошибка игры.", True)
        return
    _, game_id, position_text = parts
    try:
        position = int(position_text)
    except ValueError:
        await answer_callback_safely(callback, "Неверная клетка.", True)
        return
    if position < 0 or position > 8:
        await answer_callback_safely(callback, "Неверная клетка.", True)
        return
    game = get_game(game_id)
    if not game:
        await answer_callback_safely(callback, "Игра уже завершена.", True)
        return
    if game["game_type"] != "ttt":
        await answer_callback_safely(callback, "Неверный тип игры.", True)
        return
    if game["state"] != "playing":
        await answer_callback_safely(callback, "Игра уже закончена.", True)
        return
    if not callback.from_user:
        return
    user_id = callback.from_user.id
    data = decode_json(game["data"])
    board = data.get("board")
    current_symbol = data.get("current_symbol")
    if not isinstance(board, list) or len(board) != 9:
        await answer_callback_safely(callback, "Данные игры повреждены.", True)
        return
    if current_symbol == TTT_HOST_SYMBOL:
        expected_id = game["host_id"]
    else:
        expected_id = game["guest_id"]
    if user_id != expected_id:
        await answer_callback_safely(callback, "Сейчас ход другого игрока.", True)
        return
    if board[position] != TTT_EMPTY:
        await answer_callback_safely(callback, "Эта клетка уже занята.", True)
        return
    board[position] = current_symbol
    winner = ttt_get_winner(board)
    if winner:
        if winner == TTT_HOST_SYMBOL:
            winner_text = "🏆 Победили крестики ❌"
        else:
            winner_text = "🏆 Победили нолики ⭕"
        data["board"] = board
        data["winner"] = winner
        update_game(game_id, state="finished", data=data)
        text = f"🎮 <b>Крестики-нолики</b>\n\n{winner_text}"
        await edit_game_message(game, text, ttt_keyboard(game_id, board))
        await answer_callback_safely(callback, "Игра завершена!")
        return
    if ttt_is_draw(board):
        data["board"] = board
        data["winner"] = "draw"
        update_game(game_id, state="finished", data=data)
        text = "🎮 <b>Крестики-нолики</b>\n\n🤝 <b>Ничья!</b>"
        await edit_game_message(game, text, ttt_keyboard(game_id, board))
        await answer_callback_safely(callback, "Ничья!")
        return
    next_symbol = TTT_GUEST_SYMBOL if current_symbol == TTT_HOST_SYMBOL else TTT_HOST_SYMBOL
    data["board"] = board
    data["current_symbol"] = next_symbol
    update_game(game_id, data=data)
    text = ttt_game_text(game, next_symbol)
    await edit_game_message(game, text, ttt_keyboard(game_id, board))
    await answer_callback_safely(callback, "Ход принят.")

#функция66
def roulette_keyboard(game_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Испытать удачу", callback_data=f"roulette:{game_id}:play")]
    ])

#функция67
async def command_roulette(message: Message, connection):
    host = message.from_user
    if not host:
        await send_business_response(message, connection, "❌ Не удалось определить игрока.")
        return
    guest_id = message.chat.id
    if guest_id == host.id:
        await send_business_response(message, connection, "❌ Нужен второй игрок.")
        return
    game_id = generate_game_id()
    text = (
        "🎯 <b>Рулетка удачи</b>\n\n"
        "Игра началась!\n\n"
        "Игроки по очереди нажимают <b>«Испытать удачу»</b>.\n\n"
        "Один из ходов случайно завершит раунд."
    )
    sent = await send_game_message(message, connection, text, roulette_keyboard(game_id))
    if not sent:
        return
    save_game(
        game_id=game_id,
        game_type="roulette",
        connection_id=connection["connection_id"],
        chat_id=message.chat.id,
        message_id=sent.message_id,
        host_id=host.id,
        guest_id=guest_id,
        state="playing",
        data={"current_player": host.id, "turn": 0, "history": []},
    )

#функция68
@dp.callback_query(F.data.startswith("roulette:"))
async def roulette_callback(callback: CallbackQuery):
    if not callback.data:
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await answer_callback_safely(callback, "Ошибка игры.", True)
        return
    _, game_id, action = parts
    if action != "play":
        return
    game = get_game(game_id)
    if not game:
        await answer_callback_safely(callback, "Игра уже завершена.", True)
        return
    if game["game_type"] != "roulette":
        return
    if game["state"] != "playing":
        await answer_callback_safely(callback, "Раунд уже завершён.", True)
        return
    if not callback.from_user:
        return
    user_id = callback.from_user.id
    if not is_game_player(game, user_id):
        await answer_callback_safely(callback, "Ты не участвуешь в этой игре.", True)
        return
    data = decode_json(game["data"])
    current_player = data.get("current_player")
    if user_id != current_player:
        await answer_callback_safely(callback, "Сейчас ход другого игрока.", True)
        return
    turn = int(data.get("turn", 0))
    history = data.get("history", [])
    turn += 1
    end_chance = min(0.10 + turn * 0.08, 0.75)
    round_ends = random.random() < end_chance
    history.append({"turn": turn, "player_id": user_id})
    if round_ends:
        opponent_id = get_opponent_id(game, user_id)
        data["turn"] = turn
        data["history"] = history
        data["loser_id"] = user_id
        data["winner_id"] = opponent_id
        update_game(game_id, state="finished", data=data)
        if user_id == game["host_id"]:
            loser_text = "Первый игрок"
            winner_text = "Второй игрок"
        else:
            loser_text = "Второй игрок"
            winner_text = "Первый игрок"
        text = (
            "🎯 <b>Рулетка удачи</b>\n\n"
            f"Раунд завершён на <b>{turn}</b> ходе.\n\n"
            f"Не повезло: <b>{loser_text}</b>\n\n"
            f"🏆 Победитель: <b>{winner_text}</b>"
        )
        await edit_game_message(game, text, None)
        await answer_callback_safely(callback, "Раунд завершён!")
        return
    next_player = get_opponent_id(game, user_id)
    data["turn"] = turn
    data["history"] = history
    data["current_player"] = next_player
    update_game(game_id, data=data)
    if next_player == game["host_id"]:
        next_player_text = "Первый игрок"
    else:
        next_player_text = "Второй игрок"
    text = (
        "🎯 <b>Рулетка удачи</b>\n\n"
        f"Ход №<b>{turn}</b> прошёл.\n\n"
        f"Теперь ходит: <b>{next_player_text}</b>"
    )
    await edit_game_message(game, text, roulette_keyboard(game_id))
    await answer_callback_safely(callback, "Удача на твоей стороне!")

#функция69
async def command_game(message: Message, connection):
    text = (
        "🎮 <b>Доступные игры</b>\n\n"
        "Выбери игру:\n"
        "<code>.dice</code> — Чёт / Нечёт (бросок кубика)\n"
        "<code>.ttt</code> — Крестики-нолики\n"
        "<code>.roulette</code> — Рулетка удачи\n\n"
        "Просто отправь команду в диалоге с ботом."
    )
    await send_business_response(message, connection, text)

init_database()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

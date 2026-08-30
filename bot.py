import asyncio
import logging
import re
import sqlite3

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    BusinessConnection,
    BusinessMessagesDeleted,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    MessageEntity,
)


# =========================================================
# bobmod TEST v0.2
# =========================================================

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

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
# Популярные часовые пояса
# =========================================================

TIMEZONES = {
    "moscow": (
        "🇷🇺 Москва — МСК",
        "Europe/Moscow",
    ),

    "almaty": (
        "🇰🇿 Алматы — КЗ",
        "Asia/Almaty",
    ),

    "astana": (
        "🇰🇿 Астана — КЗ",
        "Asia/Almaty",
    ),

    "kyiv": (
        "🇺🇦 Киев",
        "Europe/Kyiv",
    ),

    "minsk": (
        "🇧🇾 Минск",
        "Europe/Minsk",
    ),

    "yerevan": (
        "🇦🇲 Ереван",
        "Asia/Yerevan",
    ),

    "tbilisi": (
        "🇬🇪 Тбилиси",
        "Asia/Tbilisi",
    ),

    "baku": (
        "🇦🇿 Баку",
        "Asia/Baku",
    ),

    "istanbul": (
        "🇹🇷 Стамбул",
        "Europe/Istanbul",
    ),

    "helsinki": (
        "🇫🇮 Хельсинки",
        "Europe/Helsinki",
    ),

    "london": (
        "🇬🇧 Лондон",
        "Europe/London",
    ),

    "berlin": (
        "🇩🇪 Берлин",
        "Europe/Berlin",
    ),

    "paris": (
        "🇫🇷 Париж",
        "Europe/Paris",
    ),

    "new_york": (
        "🇺🇸 Нью-Йорк",
        "America/New_York",
    ),

    "los_angeles": (
        "🇺🇸 Лос-Анджелес",
        "America/Los_Angeles",
    ),

    "dubai": (
        "🇦🇪 Дубай",
        "Asia/Dubai",
    ),

    "delhi": (
        "🇮🇳 Дели",
        "Asia/Kolkata",
    ),

    "beijing": (
        "🇨🇳 Пекин",
        "Asia/Shanghai",
    ),

    "tokyo": (
        "🇯🇵 Токио",
        "Asia/Tokyo",
    ),

    "seoul": (
        "🇰🇷 Сеул",
        "Asia/Seoul",
    ),
}


# =========================================================
# Логирование
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


# =========================================================
# Bot
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# FSM
# =========================================================

class SettingsState(StatesGroup):
    waiting_timezone = State()


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

                is_enabled INTEGER NOT NULL DEFAULT 1,

                base_first_name TEXT,
                base_last_name TEXT,

                can_reply INTEGER NOT NULL DEFAULT 0,
                can_edit_name INTEGER NOT NULL DEFAULT 0
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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                connection_id TEXT PRIMARY KEY,

                time_enabled INTEGER NOT NULL DEFAULT 0,

                timezone TEXT NOT NULL DEFAULT 'Europe/Moscow',

                time_format TEXT NOT NULL DEFAULT '24',

                show_seconds INTEGER NOT NULL DEFAULT 0,

                time_position TEXT NOT NULL DEFAULT 'after',

                message_style TEXT NOT NULL DEFAULT 'off',

                last_applied_time TEXT
            )
        """)

        conn.commit()


# =========================================================
# Business connections
# =========================================================

def save_connection(
    connection: BusinessConnection,
):
    rights = connection.rights

    can_reply = bool(
        getattr(rights, "can_reply", False)
    )

    can_edit_name = bool(
        getattr(rights, "can_edit_name", False)
        or
        getattr(rights, "can_change_name", False)
    )

    with get_connection() as conn:

        existing = conn.execute("""
            SELECT *
            FROM business_connections
            WHERE connection_id = ?
        """, (
            connection.id,
        )).fetchone()

        if existing:

            conn.execute("""
                UPDATE business_connections

                SET owner_id = ?,
                    is_enabled = ?,
                    can_reply = ?,
                    can_edit_name = ?

                WHERE connection_id = ?
            """, (
                connection.user.id,
                int(connection.is_enabled),
                int(can_reply),
                int(can_edit_name),
                connection.id,
            ))

        else:

            conn.execute("""
                INSERT INTO business_connections (
                    connection_id,
                    owner_id,
                    is_enabled,

                    base_first_name,
                    base_last_name,

                    can_reply,
                    can_edit_name
                )

                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                connection.id,
                connection.user.id,
                int(connection.is_enabled),

                connection.user.first_name,
                connection.user.last_name,

                int(can_reply),
                int(can_edit_name),
            ))

            conn.execute("""
                INSERT OR IGNORE INTO settings (
                    connection_id
                )
                VALUES (?)
            """, (
                connection.id,
            ))

        conn.commit()


def get_connection_for_user(user_id: int):
    with get_connection() as conn:

        return conn.execute("""
            SELECT *
            FROM business_connections
            WHERE owner_id = ?
              AND is_enabled = 1
            ORDER BY rowid DESC
            LIMIT 1
        """, (
            user_id,
        )).fetchone()


def get_connection_by_id(connection_id: str):
    with get_connection() as conn:

        return conn.execute("""
            SELECT *
            FROM business_connections
            WHERE connection_id = ?
        """, (
            connection_id,
        )).fetchone()


# =========================================================
# Settings
# =========================================================

def get_settings(connection_id: str):
    with get_connection() as conn:

        row = conn.execute("""
            SELECT *
            FROM settings
            WHERE connection_id = ?
        """, (
            connection_id,
        )).fetchone()

        if not row:

            conn.execute("""
                INSERT INTO settings (
                    connection_id
                )
                VALUES (?)
            """, (
                connection_id,
            ))

            conn.commit()

            return conn.execute("""
                SELECT *
                FROM settings
                WHERE connection_id = ?
            """, (
                connection_id,
            )).fetchone()

        return row


def update_setting(
    connection_id: str,
    field: str,
    value,
):
    allowed = {
        "time_enabled",
        "timezone",
        "time_format",
        "show_seconds",
        "time_position",
        "message_style",
        "last_applied_time",
    }

    if field not in allowed:
        raise ValueError(
            "Unknown setting"
        )

    with get_connection() as conn:

        conn.execute(
            f"""
            UPDATE settings
            SET {field} = ?
            WHERE connection_id = ?
            """,
            (
                value,
                connection_id,
            )
        )

        conn.commit()


# =========================================================
# Messages DB
# =========================================================

def save_message(
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
    created_at,
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

            VALUES (
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?
            )
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

            created_at,
        ))

        conn.commit()


def get_message(
    connection_id,
    chat_id,
    message_id,
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
            message_id,
        )).fetchone()


def mark_edited(
    connection_id,
    chat_id,
    message_id,
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
            message_id,
        ))

        conn.commit()


def mark_deleted(
    connection_id,
    chat_id,
    message_id,
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
            message_id,
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
# Timezone helpers
# =========================================================

UTC_OFFSET_RE = re.compile(
    r"^UTC([+-])(\d{1,2})(?::?(\d{2}))?$",
    re.IGNORECASE,
)


def parse_timezone(value: str):
    """
    Принимает:
        Europe/Moscow
        Asia/Almaty
        UTC+3
        UTC+05:30
    """

    value = value.strip()

    match = UTC_OFFSET_RE.match(value)

    if match:

        sign = 1 if match.group(1) == "+" else -1

        hours = int(
            match.group(2)
        )

        minutes = int(
            match.group(3) or 0
        )

        if hours > 14 or minutes > 59:
            return None

        offset = timedelta(
            hours=hours,
            minutes=minutes,
        ) * sign

        return timezone(
            offset,
            name=value.upper(),
        )

    try:

        return ZoneInfo(value)

    except ZoneInfoNotFoundError:

        return None


def timezone_label(zone_name: str):
    for key, data in TIMEZONES.items():

        if data[1] == zone_name:
            return data[0]

    return zone_name


def get_now_for_timezone(zone_name: str):
    tz = parse_timezone(zone_name)

    if tz is None:
        tz = ZoneInfo("Europe/Moscow")

    return datetime.now(tz)


# =========================================================
# Time formatting
# =========================================================

def format_current_time(settings):
    now = get_now_for_timezone(
        settings["timezone"]
    )

    if settings["time_format"] == "12":

        fmt = "%I:%M"

        if settings["show_seconds"]:
            fmt = "%I:%M:%S"

        return now.strftime(fmt).lstrip("0") + (
            " " + now.strftime("%p")
        )

    fmt = "%H:%M"

    if settings["show_seconds"]:
        fmt = "%H:%M:%S"

    return now.strftime(fmt)


# =========================================================
# Time in profile
# =========================================================

async def apply_time_to_name(
    connection_id: str,
):
    connection = get_connection_by_id(
        connection_id
    )

    if not connection:
        return

    settings = get_settings(
        connection_id
    )

    if not settings["time_enabled"]:
        return

    if not connection["is_enabled"]:
        return

    if not connection["can_edit_name"]:
        return

    current_time = format_current_time(
        settings
    )

    if settings["last_applied_time"] == current_time:
        return

    base_first = (
        connection["base_first_name"]
        or "Business"
    )

    base_last = (
        connection["base_last_name"]
        or ""
    )

    if settings["time_position"] == "before":

        new_first = (
            f"{current_time} | {base_first}"
        )

    else:

        new_first = (
            f"{base_first} | {current_time}"
        )

    # Telegram: first_name max 64 characters.
    new_first = new_first[:64]

    try:

        await bot.set_business_account_name(
            business_connection_id=connection_id,
            first_name=new_first,
            last_name=base_last,
        )

        update_setting(
            connection_id,
            "last_applied_time",
            current_time,
        )

        logging.info(
            "Updated Business name | "
            "connection=%s | time=%s",
            connection_id,
            current_time,
        )

    except TelegramBadRequest as error:

        logging.warning(
            "Could not change Business name: %s",
            error,
        )

    except TelegramForbiddenError as error:

        logging.warning(
            "No permission to change Business name: %s",
            error,
        )


async def time_updater():
    while True:

        try:

            with get_connection() as conn:

                rows = conn.execute("""
                    SELECT connection_id
                    FROM settings
                    WHERE time_enabled = 1
                """).fetchall()

            for row in rows:

                try:
                    await apply_time_to_name(
                        row["connection_id"]
                    )

                except Exception:

                    logging.exception(
                        "Time update error"
                    )

        except Exception:

            logging.exception(
                "Time updater error"
            )

        # Проверяем каждые 20 секунд,
        # но меняем имя только при смене отображаемого времени.
        await asyncio.sleep(20)


# =========================================================
# Message formatting
# =========================================================

def utf16_length(text: str):
    return len(
        text.encode("utf-16-le")
    ) // 2


def style_entities(
    text: str,
    style: str,
):
    if not text:
        return []

    length = utf16_length(text)

    if style == "bold":

        return [
            MessageEntity(
                type="bold",
                offset=0,
                length=length,
            )
        ]

    if style == "italic":

        return [
            MessageEntity(
                type="italic",
                offset=0,
                length=length,
            )
        ]

    if style == "mono":

        return [
            MessageEntity(
                type="code",
                offset=0,
                length=length,
            )
        ]

    if style == "quote":

        return [
            MessageEntity(
                type="blockquote",
                offset=0,
                length=length,
            )
        ]

    return []


def style_label(style: str):
    return {
        "off": "Выключено",
        "bold": "Жирный",
        "italic": "Курсив",
        "mono": "Моноширинный",
        "quote": "Цитата",
    }.get(
        style,
        "Выключено",
    )


# =========================================================
# Settings keyboards
# =========================================================

def settings_keyboard(
    connection_id: str,
):
    settings = get_settings(
        connection_id
    )

    time_status = (
        "✅"
        if settings["time_enabled"]
        else "❌"
    )

    message_status = style_label(
        settings["message_style"]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🕐 Время в имени {time_status}",
                    callback_data="settings:time",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💬 Сообщения: {message_status}",
                    callback_data="settings:messages",
                )
            ],
        ]
    )


def time_keyboard(
    connection_id: str,
):
    settings = get_settings(
        connection_id
    )

    enabled = (
        "Выключить"
        if settings["time_enabled"]
        else "Включить"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🕐 {enabled}",
                    callback_data="time:toggle",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌍 Часовой пояс",
                    callback_data="time:timezone",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Формат времени",
                    callback_data="time:format",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📍 Положение времени",
                    callback_data="time:position",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔢 Секунды",
                    callback_data="time:seconds",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="settings:main",
                )
            ],
        ]
    )


def timezone_keyboard():
    buttons = []

    for key, data in TIMEZONES.items():

        buttons.append([
            InlineKeyboardButton(
                text=data[0],
                callback_data=f"tz:{key}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="✏️ Свой часовой пояс",
            callback_data="tz:custom",
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="settings:time",
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def format_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="24 часа — 15:31",
                    callback_data="format:24",
                )
            ],
            [
                InlineKeyboardButton(
                    text="12 часов — 3:31 PM",
                    callback_data="format:12",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="settings:time",
                )
            ],
        ]
    )


def position_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Имя | 15:31",
                    callback_data="position:after",
                )
            ],
            [
                InlineKeyboardButton(
                    text="15:31 | Имя",
                    callback_data="position:before",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="settings:time",
                )
            ],
        ]
    )


def message_style_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Выключено",
                    callback_data="style:off",
                )
            ],
            [
                InlineKeyboardButton(
                    text="𝐀 Жирный",
                    callback_data="style:bold",
                )
            ],
            [
                InlineKeyboardButton(
                    text="𝘈 Курсив",
                    callback_data="style:italic",
                )
            ],
            [
                InlineKeyboardButton(
                    text="`Моно`",
                    callback_data="style:mono",
                )
            ],
            [
                InlineKeyboardButton(
                    text="▎ Цитата",
                    callback_data="style:quote",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="settings:main",
                )
            ],
        ]
    )


# =========================================================
# Settings text
# =========================================================

def settings_text(
    connection_id: str,
):
    connection = get_connection_by_id(
        connection_id
    )

    settings = get_settings(
        connection_id
    )

    if not connection:
        return (
            "❌ Business-подключение не найдено."
        )

    time_enabled = (
        "включено"
        if settings["time_enabled"]
        else "выключено"
    )

    if settings["time_format"] == "24":
        fmt = "24 часа"
    else:
        fmt = "12 часов"

    seconds = (
        "включены"
        if settings["show_seconds"]
        else "выключены"
    )

    position = (
        "после имени"
        if settings["time_position"] == "after"
        else "перед именем"
    )

    return (
        "🤖 <b>bobmod TEST v0.2</b>\n\n"
        "⚙️ <b>Настройки</b>\n\n"

        f"🕐 Время в имени: <b>{time_enabled}</b>\n"
        f"🌍 Часовой пояс: "
        f"<b>{timezone_label(settings['timezone'])}</b>\n"
        f"📝 Формат: <b>{fmt}</b>\n"
        f"🔢 Секунды: <b>{seconds}</b>\n"
        f"📍 Положение: <b>{position}</b>\n\n"

        f"💬 Сообщения: "
        f"<b>{style_label(settings['message_style'])}</b>"
    )


# =========================================================
# Permission helper
# =========================================================

async def require_connection(
    user_id: int,
):
    connection = get_connection_for_user(
        user_id
    )

    if not connection:
        return None, (
            "❌ У тебя нет активного "
            "Business-подключения bobmod."
        )

    return connection, None


# =========================================================
# /settings
# Только ЛС с ботом
# =========================================================

@dp.message(
    Command("settings"),
    F.chat.type == "private",
)
async def settings_command(
    message: Message,
):
    if not message.from_user:
        return

    connection, error = await require_connection(
        message.from_user.id
    )

    if error:

        await message.answer(
            error
        )

        return

    await message.answer(
        settings_text(
            connection["connection_id"]
        ),
        parse_mode="HTML",
        reply_markup=settings_keyboard(
            connection["connection_id"]
        ),
    )


# =========================================================
# Settings main
# =========================================================

@dp.callback_query(
    F.data == "settings:main"
)
async def settings_main_callback(
    callback: CallbackQuery,
):
    if not callback.from_user:
        return

    connection, error = await require_connection(
        callback.from_user.id
    )

    if error:

        await callback.answer(
            "Нет активного Business-подключения.",
            show_alert=True,
        )

        return

    await callback.message.edit_text(
        settings_text(
            connection["connection_id"]
        ),
        parse_mode="HTML",
        reply_markup=settings_keyboard(
            connection["connection_id"]
        ),
    )

    await callback.answer()


# =========================================================
# Время в имени
# =========================================================

@dp.callback_query(
    F.data == "settings:time"
)
async def settings_time_callback(
    callback: CallbackQuery,
):
    connection, error = await require_connection(
        callback.from_user.id
    )

    if error:

        await callback.answer(
            "Нет Business-подключения.",
            show_alert=True,
        )

        return

    settings = get_settings(
        connection["connection_id"]
    )

    status = (
        "включено"
        if settings["time_enabled"]
        else "выключено"
    )

    permission = (
        "✅ Есть"
        if connection["can_edit_name"]
        else "❌ Нет"
    )

    text = (
        "🕐 <b>Время в имени</b>\n\n"

        f"Статус: <b>{status}</b>\n"
        f"Часовой пояс: "
        f"<b>{timezone_label(settings['timezone'])}</b>\n\n"

        "Для этой функции требуется разрешение "
        "на изменение имени и фамилии Business-аккаунта.\n\n"

        f"Разрешение: <b>{permission}</b>"
    )

    if not connection["can_edit_name"]:

        text += (
            "\n\n"
            "⚠️ Открой настройки подключения bobmod "
            "и разреши ему изменять имя и фамилию "
            "Business-аккаунта."
        )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=time_keyboard(
            connection["connection_id"]
        ),
    )

    await callback.answer()


# =========================================================
# Toggle time
# =========================================================

@dp.callback_query(
    F.data == "time:toggle"
)
async def time_toggle_callback(
    callback: CallbackQuery,
):
    connection, error = await require_connection(
        callback.from_user.id
    )

    if error:

        await callback.answer(
            "Нет Business-подключения.",
            show_alert=True,
        )

        return

    if not connection["can_edit_name"]:

        await callback.answer(
            "Нужно разрешение на изменение имени.",
            show_alert=True,
        )

        return

    settings = get_settings(
        connection["connection_id"]
    )

    new_value = not bool(
        settings["time_enabled"]
    )

    update_setting(
        connection["connection_id"],
        "time_enabled",
        int(new_value),
    )

    if new_value:

        update_setting(
            connection["connection_id"],
            "last_applied_time",
            None,
        )

        await apply_time_to_name(
            connection["connection_id"]
        )

        await callback.answer(
            "Время в имени включено."
        )

    else:

        # Возвращаем исходное имя.
        try:

            await bot.set_business_account_name(
                business_connection_id=connection[
                    "connection_id"
                ],
                first_name=(
                    connection["base_first_name"]
                    or "Business"
                ),
                last_name=(
                    connection["base_last_name"]
                    or None
                ),
            )

            update_setting(
                connection["connection_id"],
                "last_applied_time",
                None,
            )

            await callback.answer(
                "Время в имени выключено."
            )

        except TelegramBadRequest:

            await callback.answer(
                "Не удалось восстановить имя.",
                show_alert=True,
            )

    await settings_time_callback(
        callback
    )


# =========================================================
# Timezone menu
# =========================================================

@dp.callback_query(
    F.data == "time:timezone"
)
async def timezone_menu_callback(
    callback: CallbackQuery,
):
    await callback.message.edit_text(
        "🌍 <b>Выбери часовой пояс</b>\n\n"
        "Можно выбрать готовый вариант "
        "или указать свой IANA-часовой пояс "
        "либо UTC-смещение.",
        parse_mode="HTML",
        reply_markup=timezone_keyboard(),
    )

    await callback.answer()


# =========================================================
# Preset timezone
# =========================================================

@dp.callback_query(
    F.data.startswith("tz:")
)
async def timezone_selected_callback(
    callback: CallbackQuery,
):
    key = callback.data.split(
        ":",
        1
    )[1]

    if key == "custom":

        await callback.message.edit_text(
            "✏️ <b>Свой часовой пояс</b>\n\n"
            "Напиши, например:\n\n"
            "<code>Europe/Moscow</code>\n"
            "<code>Asia/Almaty</code>\n"
            "<code>UTC+3</code>\n"
            "<code>UTC+05:30</code>",
            parse_mode="HTML",
        )

        await settings_state_for_timezone(
            callback
        )

        await callback.answer()

        return

    if key not in TIMEZONES:

        await callback.answer(
            "Неизвестный часовой пояс.",
            show_alert=True,
        )

        return

    connection, error = await require_connection(
        callback.from_user.id
    )

    if error:

        await callback.answer(
            error,
            show_alert=True,
        )

        return

    zone_name = TIMEZONES[key][1]

    update_setting(
        connection["connection_id"],
        "timezone",
        zone_name,
    )

    update_setting(
        connection["connection_id"],
        "last_applied_time",
        None,
    )

    await apply_time_to_name(
        connection["connection_id"]
    )

    await callback.message.edit_text(
        "✅ <b>Часовой пояс изменён</b>\n\n"
        f"🌍 {TIMEZONES[key][0]}",
        parse_mode="HTML",
        reply_markup=time_keyboard(
            connection["connection_id"]
        ),
    )

    await callback.answer()


async def settings_state_for_timezone(
    callback: CallbackQuery,
):
    # Состояние создаётся на пользователя.
    # connection_id сохраняем в FSM.
    connection, _ = await require_connection(
        callback.from_user.id
    )

    if connection:

        # Получаем FSM через dispatcher не нужно:
        # используем временный storage через state middleware
        pass


# =========================================================
# ВАЖНО:
# Для callback выше используем отдельный словарь ожиданий.
# Он подходит для небольшой тестовой версии.
# =========================================================

waiting_timezone_users = set()


# Переопределяем логику custom timezone:
@dp.callback_query(
    F.data == "tz:custom"
)
async def custom_timezone_callback(
    callback: CallbackQuery,
):
    connection, error = await require_connection(
        callback.from_user.id
    )

    if error:

        await callback.answer(
            error,
            show_alert=True,
        )

        return

    waiting_timezone_users.add(
        callback.from_user.id
    )

    await callback.message.edit_text(
        "✏️ <b>Свой часовой пояс</b>\n\n"
        "Напиши его следующим сообщением.\n\n"
        "Примеры:\n"
        "<code>Europe/Moscow</code>\n"
        "<code>Asia/Almaty</code>\n"
        "<code>America/New_York</code>\n"
        "<code>UTC+3</code>\n"
        "<code>UTC+05:30</code>\n\n"
        "Для отмены отправь <code>/cancel</code>.",
        parse_mode="HTML",
    )

    await callback.answer()


# =========================================================
# Custom timezone text
# =========================================================

@dp.message(
    F.chat.type == "private",
    F.text,
)
async def private_text_handler(
    message: Message,
):
    if not message.from_user:
        return

    user_id = message.from_user.id

    if user_id not in waiting_timezone_users:
        return

    text = message.text.strip()

    if text.lower() == "/cancel":

        waiting_timezone_users.discard(
            user_id
        )

        await message.answer(
            "❌ Выбор часового пояса отменён."
        )

        return

    zone = parse_timezone(text)

    if zone is None:

        await message.answer(
            "❌ Не удалось распознать часовой пояс.\n\n"
            "Попробуй, например:\n"
            "<code>Europe/Moscow</code>\n"
            "<code>Asia/Almaty</code>\n"
            "<code>UTC+3</code>",
            parse_mode="HTML",
        )

        return

    connection, error = await require_connection(
        user_id
    )

    if error:

        waiting_timezone_users.discard(
            user_id
        )

        await message.answer(
            error
        )

        return

    zone_name = text

    # Нормализуем IANA.
    if isinstance(zone, ZoneInfo):

        zone_name = zone.key

    elif isinstance(zone, timezone):

        zone_name = text.upper()

    update_setting(
        connection["connection_id"],
        "timezone",
        zone_name,
    )

    update_setting(
        connection["connection_id"],
        "last_applied_time",
        None,
    )

    waiting_timezone_users.discard(
        user_id
    )

    await apply_time_to_name(
        connection["connection_id"]
    )

    await message.answer(
        "✅ <b>Часовой пояс сохранён</b>\n\n"
        f"🌍 <code>{zone_name}</code>",
        parse_mode="HTML",
        reply_markup=settings_keyboard(
            connection["connection_id"]
        ),
    )


# =========================================================
# Time format
# =========================================================

@dp.callback_query(
    F.data == "time:format"
)
async def time_format_menu(
    callback: CallbackQuery,
):
    await callback.message.edit_text(
        "📝 <b>Формат времени</b>\n\n"
        "Выбери нужный формат.",
        parse_mode="HTML",
        reply_markup=format_keyboard(),
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("format:")
)
async def time_format_selected(
    callback: CallbackQuery,
):
    connection, error = await require_connection(
        callback.from_user.id
    )

    if error:

        await callback.answer(
            error,
            show_alert=True,
        )

        return

    fmt = callback.data.split(
        ":",
        1
    )[1]

    if fmt not in ("12", "24"):
        return

    update_setting(
        connection["connection_id"],
        "time_format",
        fmt,
    )

    update_setting(
        connection["connection_id"],
        "last_applied_time",
        None,
    )

    await apply_time_to_name(
        connection["connection_id"]
    )

    await callback.answer(
        "Формат изменён."
    )

    await settings_time_callback(
        callback
    )


# =========================================================
# Position
# =========================================================

@dp.callback_query(
    F.data == "time:position"
)
async def time_position_menu(
    callback: CallbackQuery,
):
    await callback.message.edit_text(
        "📍 <b>Положение времени</b>\n\n"
        "Как должно выглядеть имя?",
        parse_mode="HTML",
        reply_markup=position_keyboard(),
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("position:")
)
async def time_position_selected(
    callback: CallbackQuery,
):
    connection, error = await require_connection(
        callback.from_user.id
    )

    if error:

        await callback.answer(
            error,
            show_alert=True,
        )

        return

    position = callback.data.split(
        ":",
        1
    )[1]

    if position not in ("before", "after"):
        return

    update_setting(
        connection["connection_id"],
        "time_position",
        position,
    )

    update_setting(
        connection["connection_id"],
        "last_applied_time",
        None,
    )

    await apply_time_to_name(
        connection["connection_id"]
    )

    await callback.answer(
        "Положение изменено."
    )

    await settings_time_callback(
        callback
    )


# =========================================================
# Seconds
# =========================================================

@dp.callback_query(
    F.data == "time:seconds"
)
async def time_seconds_toggle(
    callback: CallbackQuery,
):
    connection, error = await require_connection(
        callback.from_user.id
    )

    if error:

        await callback.answer(
            error,
            show_alert=True,
        )

        return

    settings = get_settings(
        connection["connection_id"]
    )

    new_value = not bool(
        settings["show_seconds"]
    )

    update_setting(
        connection["connection_id"],
        "show_seconds",
        int(new_value),
    )

    update_setting(
        connection["connection_id"],
        "last_applied_time",
        None,
    )

    await apply_time_to_name(
        connection["connection_id"]
    )

    await callback.answer(
        "Секунды включены."
        if new_value
        else
        "Секунды выключены."
    )

    await settings_time_callback(
        callback
    )


# =========================================================
# Message styles
# =========================================================

@dp.callback_query(
    F.data == "settings:messages"
)
async def messages_settings_callback(
    callback: CallbackQuery,
):
    connection, error = await require_connection(
        callback.from_user.id
    )

    if error:

        await callback.answer(
            error,
            show_alert=True,
        )

        return

    can_reply = bool(
        connection["can_reply"]
    )

    text = (
        "💬 <b>Настройки сообщений</b>\n\n"
        "Выбранный стиль применяется "
        "к обычным текстовым сообщениям, "
        "которые владелец Business-аккаунта "
        "отправляет в своих диалогах.\n\n"
        "Стиль не применяется к командам "
        "bobmod."
    )

    if not can_reply:

        text += (
            "\n\n"
            "⚠️ У bobmod нет разрешения "
            "на отправку и редактирование "
            "Business-сообщений.\n\n"
            "Разреши боту отвечать/редактировать "
            "сообщения в настройках Business-подключения."
        )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=message_style_keyboard(),
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("style:")
)
async def message_style_selected(
    callback: CallbackQuery,
):
    connection, error = await require_connection(
        callback.from_user.id
    )

    if error:

        await callback.answer(
            error,
            show_alert=True,
        )

        return

    style = callback.data.split(
        ":",
        1
    )[1]

    allowed = {
        "off",
        "bold",
        "italic",
        "mono",
        "quote",
    }

    if style not in allowed:
        return

    if (
        style != "off"
        and not connection["can_reply"]
    ):

        await callback.answer(
            "Нужно разрешение на отправку "
            "и редактирование Business-сообщений.",
            show_alert=True,
        )

        return

    update_setting(
        connection["connection_id"],
        "message_style",
        style,
    )

    await callback.answer(
        "Стиль сохранён."
    )

    await messages_settings_callback(
        callback
    )


# =========================================================
# Business Connection
# =========================================================

@dp.business_connection()
async def business_connection_handler(
    connection: BusinessConnection,
):

    logging.info(
        "Business connection | "
        "id=%s | owner=%s | enabled=%s",
        connection.id,
        connection.user.id,
        connection.is_enabled,
    )

    save_connection(
        connection
    )

    if connection.user.id != OWNER_ID:
        return

    if connection.is_enabled:

        await bot.send_message(
            chat_id=OWNER_ID,
            text=(
                "🤖 <b>bobmod TEST v0.2</b>\n\n"
                "Business-подключение включено ✅"
            ),
            parse_mode="HTML",
        )

    else:

        await bot.send_message(
            chat_id=OWNER_ID,
            text=(
                "🤖 <b>bobmod TEST v0.2</b>\n\n"
                "Business-подключение отключено ❌"
            ),
            parse_mode="HTML",
        )


# =========================================================
# Business Message
# =========================================================

@dp.business_message()
async def business_message_handler(
    message: Message,
):

    if message.chat.type != "private":
        return

    connection_id = (
        message.business_connection_id
    )

    if not connection_id:
        return

    connection = get_connection_by_id(
        connection_id
    )

    if not connection:
        return

    # -----------------------------------------------------
    # Сохраняем сообщение
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
        media_file_id = (
            message.video.file_id
        )

    elif message.document:

        media_type = "document"
        media_file_id = (
            message.document.file_id
        )

    elif message.audio:

        media_type = "audio"
        media_file_id = (
            message.audio.file_id
        )

    elif message.voice:

        media_type = "voice"
        media_file_id = (
            message.voice.file_id
        )

    elif message.animation:

        media_type = "animation"
        media_file_id = (
            message.animation.file_id
        )

    elif message.sticker:

        media_type = "sticker"
        media_file_id = (
            message.sticker.file_id
        )

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

        created_at=message.date.isoformat(),
    )

    # =====================================================
    # COMMANDS
    # =====================================================

    if message.text:

        command = (
            message.text
            .strip()
            .lower()
        )

        if command == ".help":

            await replace_command_message(
                message,
                (
                    "🤖 <b>bobmod TEST</b>\n\n"
                    "Доступные команды:\n\n"
                    "• <code>.help</code> — помощь\n"
                    "• <code>.info</code> — информация\n"
                    "• <code>.ping</code> — проверка работы"
                ),
                connection_id,
            )

            return

        if command == ".ping":

            await replace_command_message(
                message,
                (
                    "🏓 <b>Pong!</b>\n"
                    "🤖 bobmod работает"
                ),
                connection_id,
            )

            return

        if command == ".info":

            name = " ".join(
                part
                for part in [
                    message.chat.first_name,
                    message.chat.last_name,
                ]
                if part
            )

            if not name:
                name = "Не указан"

            username = (
                f"@{message.chat.username}"
                if message.chat.username
                else "Не указан"
            )

            text = (
                "👤 <b>Информация</b>\n\n"
                f"🆔 <b>ID:</b> "
                f"<code>{message.chat.id}</code>\n"
                f"👤 <b>Имя:</b> "
                f"{name}\n"
                f"🔗 <b>Username:</b> "
                f"{username}"
            )

            await replace_command_message(
                message,
                text,
                connection_id,
            )

            return

    # =====================================================
    # АВТОФОРМАТИРОВАНИЕ СООБЩЕНИЙ
    # =====================================================

    settings = get_settings(
        connection_id
    )

    style = settings["message_style"]

    if style == "off":
        return

    if not message.text:
        return

    # Только сообщения владельца Business-аккаунта.
    # Сообщения собеседника A не форматируем.
    if not message.from_user:
        return

    if message.from_user.id != connection["owner_id"]:
        return

    # Не трогаем команды.
    if message.text.startswith(
        (".", "/")
    ):
        return

    # Inline keyboard может мешать редактированию.
    if message.reply_markup:
        return

    entities = style_entities(
        message.text,
        style,
    )

    if not entities:
        return

    try:

        await bot.edit_message_text(
            business_connection_id=connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=message.text,
            entities=entities,
        )

        logging.info(
            "Message formatted | "
            "style=%s | chat=%s | message=%s",
            style,
            message.chat.id,
            message.message_id,
        )

    except TelegramBadRequest as error:

        logging.warning(
            "Could not format message: %s",
            error,
        )

    except TelegramForbiddenError as error:

        logging.warning(
            "No permission to format message: %s",
            error,
        )


# =========================================================
# Replace command message
# =========================================================

async def replace_command_message(
    message: Message,
    text: str,
    connection_id: str,
):
    """
    Сначала пытаемся изменить команду.

    Если Telegram не разрешает редактирование:
    1. отправляем результат от имени Business;
    2. удаляем исходную команду.
    """

    try:

        await bot.edit_message_text(
            business_connection_id=connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=text,
            parse_mode="HTML",
        )

        return

    except (
        TelegramBadRequest,
        TelegramForbiddenError,
    ) as error:

        logging.warning(
            "Could not edit command: %s",
            error,
        )

    # Fallback.
    try:

        await bot.send_message(
            business_connection_id=connection_id,
            chat_id=message.chat.id,
            text=text,
            parse_mode="HTML",
        )

    except Exception:

        logging.exception(
            "Fallback send failed"
        )

        return

    # Удаляем команду.
    try:

        await bot.delete_business_messages(
            business_connection_id=connection_id,
            chat_id=message.chat.id,
            message_ids=[
                message.message_id
            ],
        )

    except Exception:

        # Старый deleteMessage как fallback.
        try:

            await bot.delete_message(
                chat_id=message.chat.id,
                message_id=message.message_id,
                business_connection_id=connection_id,
            )

        except Exception:

            logging.warning(
                "Could not delete command message"
            )


# =========================================================
# Edited Business Message
# =========================================================

@dp.edited_business_message()
async def edited_business_message_handler(
    message: Message,
):

    if message.chat.type != "private":
        return

    connection_id = (
        message.business_connection_id
    )

    if not connection_id:
        return

    row = get_message(
        connection_id,
        message.chat.id,
        message.message_id,
    )

    if not row:
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

    alert = (
        "✏️ <b>Сообщение отредактировано</b>\n\n"
        f"<b>Отправитель:</b> {sender_name}\n"
        f"<b>ID:</b> <code>{sender_id}</code>\n\n"
        f"<b>Исходный текст:</b>\n"
        f"{original_text}"
    )

    try:

        await bot.send_message(
            chat_id=OWNER_ID,
            text=alert,
            parse_mode="HTML",
        )

    except Exception:

        logging.exception(
            "Could not notify owner about edit"
        )

    mark_edited(
        connection_id,
        message.chat.id,
        message.message_id,
    )


# =========================================================
# Deleted Business Messages
# =========================================================

@dp.deleted_business_messages()
async def deleted_business_messages_handler(
    deleted: BusinessMessagesDeleted,
):

    if deleted.chat.type != "private":
        return

    connection_id = (
        deleted.business_connection_id
    )

    for message_id in deleted.message_ids:

        row = get_message(
            connection_id,
            deleted.chat.id,
            message_id,
        )

        if not row:
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

        alert = (
            "🗑️ <b>Сообщение удалено</b>\n\n"
            f"<b>Отправитель:</b> {sender_name}\n"
            f"<b>ID:</b> <code>{sender_id}</code>\n\n"
            f"<b>Исходное содержимое:</b>\n"
            f"{original_text}"
        )

        try:

            await bot.send_message(
                chat_id=OWNER_ID,
                text=alert,
                parse_mode="HTML",
            )

        except Exception:

            logging.exception(
                "Could not notify owner about deletion"
            )

        mark_deleted(
            connection_id,
            deleted.chat.id,
            message_id,
        )


# =========================================================
# /start
# =========================================================

@dp.message(
    Command("start"),
    F.chat.type == "private",
)
async def start_handler(
    message: Message,
):

    if not message.from_user:
        return

    user_id = message.from_user.id

    if user_id == OWNER_ID:

        await message.answer(
            "🤖 <b>bobmod TEST v0.2</b>\n\n"
            "Business-бот работает.\n\n"
            "В ЛС доступны:\n"
            "• <code>/settings</code> — настройки\n"
            "• <code>/stats</code> — статистика\n\n"
            "В Business-чатах:\n"
            "• <code>.help</code>\n"
            "• <code>.info</code>\n"
            "• <code>.ping</code>",
            parse_mode="HTML",
        )

        return

    if user_id in TESTER_IDS:

        await message.answer(
            "🤖 <b>bobmod TEST</b>\n\n"
            "🧪 Ты находишься в тестовой группе.\n\n"
            "Доступные команды:\n"
            "• <code>/settings</code> — настройки\n"
            "• <code>.help</code>\n"
            "• <code>.info</code>\n"
            "• <code>.ping</code>\n\n"
            "⚠️ <code>/stats</code> недоступна.",
            parse_mode="HTML",
        )


# =========================================================
# /stats
# =========================================================

@dp.message(
    Command("stats"),
    F.chat.type == "private",
)
async def stats_handler(
    message: Message,
):

    if not message.from_user:
        return

    if message.from_user.id != OWNER_ID:
        return

    stats = get_stats()

    await message.answer(
        "📊 <b>bobmod TEST v0.2</b>\n\n"
        f"💬 Сообщений: "
        f"<b>{stats['total']}</b>\n"
        f"✏️ Редактировано: "
        f"<b>{stats['edited']}</b>\n"
        f"🗑️ Удалено: "
        f"<b>{stats['deleted']}</b>",
        parse_mode="HTML",
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    init_db()

    logging.info(
        "Starting bobmod TEST v0.2..."
    )

    updater_task = asyncio.create_task(
        time_updater()
    )

    try:

        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "business_connection",
                "business_message",
                "edited_business_message",
                "deleted_business_messages",
                "callback_query",
            ],
        )

    finally:

        updater_task.cancel()

        try:
            await updater_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        logging.info(
            "bobmod TEST stopped"
    )

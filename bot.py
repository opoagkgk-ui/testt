import asyncio
import logging
import sqlite3

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    BusinessConnection,
    BusinessMessagesDeleted,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    MessageEntity,
)
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
)


# ============================================================
# bobmod TEST v0.3
# ============================================================


BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

OWNER_ID = 8371473442

TESTER_IDS = {
    5158759132,
}

DATABASE = "bobmod.db"


# ============================================================
# CUSTOM PREMIUM EMOJI
# ============================================================

CUSTOM_EMOJI = {
    "🤖": "5444921463536641665",
    "🏓": "5444921463536641665",
    "👤": "5445223416917422632",
    "🆔": "5445094086862205639",
    "🔗": "5445354937405958522",
    "📊": "5444858026869679390",
    "💬": "5445354937405958522",
    "✏️": "5447635509205559163",
    "🗑️": "5445265116754897405",
    "✅": "5445324421663320898",
    "❌": "5445267294303314527",
}


# ============================================================
# TIMEZONES
# ============================================================

TIMEZONES = {
    "moscow": ("🇷🇺 Москва — МСК", "Europe/Moscow"),
    "almaty": ("🇰🇿 Алматы", "Asia/Almaty"),
    "astana": ("🇰🇿 Астана", "Asia/Almaty"),
    "kyiv": ("🇺🇦 Киев", "Europe/Kyiv"),
    "minsk": ("🇧🇾 Минск", "Europe/Minsk"),
    "yerevan": ("🇦🇲 Ереван", "Asia/Yerevan"),
    "tbilisi": ("🇬🇪 Тбилиси", "Asia/Tbilisi"),
    "baku": ("🇦🇿 Баку", "Asia/Baku"),
    "istanbul": ("🇹🇷 Стамбул", "Europe/Istanbul"),
    "helsinki": ("🇫🇮 Хельсинки", "Europe/Helsinki"),
    "london": ("🇬🇧 Лондон", "Europe/London"),
    "berlin": ("🇩🇪 Берлин", "Europe/Berlin"),
    "paris": ("🇫🇷 Париж", "Europe/Paris"),
    "newyork": ("🇺🇸 Нью-Йорк", "America/New_York"),
    "losangeles": ("🇺🇸 Лос-Анджелес", "America/Los_Angeles"),
    "dubai": ("🇦🇪 Дубай", "Asia/Dubai"),
    "delhi": ("🇮🇳 Дели", "Asia/Kolkata"),
    "beijing": ("🇨🇳 Пекин", "Asia/Shanghai"),
    "tokyo": ("🇯🇵 Токио", "Asia/Tokyo"),
    "seoul": ("🇰🇷 Сеул", "Asia/Seoul"),
}


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


# ============================================================
# BOT
# ============================================================

bot = Bot(BOT_TOKEN)

dp = Dispatcher()


# ============================================================
# CUSTOM EMOJI ENTITIES
# ============================================================

def utf16_length(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def custom_emoji_entities(text: str):
    """
    Превращает обычные emoji из CUSTOM_EMOJI
    в настоящие Telegram Premium Custom Emoji.
    """

    entities = []

    for emoji, emoji_id in CUSTOM_EMOJI.items():

        start = 0

        while True:

            index = text.find(emoji, start)

            if index == -1:
                break

            before = text[:index]

            offset = utf16_length(before)

            length = utf16_length(emoji)

            entities.append(
                MessageEntity(
                    type="custom_emoji",
                    offset=offset,
                    length=length,
                    custom_emoji_id=emoji_id,
                )
            )

            start = index + len(emoji)

    return entities


async def send_custom(
    chat_id: int,
    text: str,
    **kwargs,
):
    return await bot.send_message(
        chat_id=chat_id,
        text=text,
        entities=custom_emoji_entities(text),
        **kwargs,
    )


# ============================================================
# DATABASE
# ============================================================

def db():
    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = db()

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_connections (
            connection_id TEXT PRIMARY KEY,
            owner_id INTEGER NOT NULL,
            enabled INTEGER DEFAULT 1,

            first_name TEXT,
            last_name TEXT,

            can_reply INTEGER DEFAULT 0,
            can_edit_name INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            connection_id TEXT PRIMARY KEY,

            time_enabled INTEGER DEFAULT 0,
            timezone TEXT DEFAULT 'Europe/Moscow',

            time_format TEXT DEFAULT '24',
            seconds INTEGER DEFAULT 0,
            time_position TEXT DEFAULT 'after',

            message_style TEXT DEFAULT 'off',

            last_time TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            connection_id TEXT,
            chat_id INTEGER,
            message_id INTEGER,

            sender_id INTEGER,
            sender_name TEXT,
            sender_username TEXT,

            text TEXT,
            caption TEXT,

            media_type TEXT,
            file_id TEXT,

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

    conn.commit()

    conn.close()


# ============================================================
# CONNECTION DATABASE
# ============================================================

def save_business_connection(
    connection: BusinessConnection,
):

    rights = connection.rights

    can_reply = bool(
        getattr(rights, "can_reply", False)
    )

    can_edit_name = bool(
        getattr(rights, "can_edit_name", False)
    )

    conn = db()

    existing = conn.execute("""
        SELECT connection_id
        FROM business_connections
        WHERE connection_id = ?
    """, (
        connection.id,
    )).fetchone()

    if existing:

        conn.execute("""
            UPDATE business_connections

            SET
                owner_id = ?,
                enabled = ?,
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
                enabled,

                first_name,
                last_name,

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

    conn.close()


def get_user_connection(user_id: int):

    conn = db()

    row = conn.execute("""
        SELECT *
        FROM business_connections

        WHERE owner_id = ?
        AND enabled = 1

        LIMIT 1
    """, (
        user_id,
    )).fetchone()

    conn.close()

    return row


def get_connection(connection_id: str):

    conn = db()

    row = conn.execute("""
        SELECT *
        FROM business_connections

        WHERE connection_id = ?
    """, (
        connection_id,
    )).fetchone()

    conn.close()

    return row


# ============================================================
# SETTINGS DATABASE
# ============================================================

def get_settings(connection_id: str):

    conn = db()

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

        row = conn.execute("""
            SELECT *
            FROM settings
            WHERE connection_id = ?
        """, (
            connection_id,
        )).fetchone()

    conn.close()

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
        "seconds",
        "time_position",
        "message_style",
        "last_time",
    }

    if field not in allowed:
        raise ValueError("Unknown setting")

    conn = db()

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

    conn.close()


# ============================================================
# MESSAGE DATABASE
# ============================================================

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
    file_id,
    created_at,
):

    conn = db()

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
            file_id,

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
        file_id,

        created_at,
    ))

    conn.commit()

    conn.close()


def get_saved_message(
    connection_id,
    chat_id,
    message_id,
):

    conn = db()

    row = conn.execute("""
        SELECT *
        FROM messages

        WHERE
            connection_id = ?
        AND
            chat_id = ?
        AND
            message_id = ?
    """, (
        connection_id,
        chat_id,
        message_id,
    )).fetchone()

    conn.close()

    return row


def mark_edited(
    connection_id,
    chat_id,
    message_id,
):

    conn = db()

    conn.execute("""
        UPDATE messages

        SET edited = 1

        WHERE
            connection_id = ?
        AND
            chat_id = ?
        AND
            message_id = ?
    """, (
        connection_id,
        chat_id,
        message_id,
    ))

    conn.commit()

    conn.close()


def mark_deleted(
    connection_id,
    chat_id,
    message_id,
):

    conn = db()

    conn.execute("""
        UPDATE messages

        SET deleted = 1

        WHERE
            connection_id = ?
        AND
            chat_id = ?
        AND
            message_id = ?
    """, (
        connection_id,
        chat_id,
        message_id,
    ))

    conn.commit()

    conn.close()


# ============================================================
# STATS
# ============================================================

def get_stats():

    conn = db()

    row = conn.execute("""
        SELECT

            COUNT(*) AS total,

            COALESCE(
                SUM(edited),
                0
            ) AS edited,

            COALESCE(
                SUM(deleted),
                0
            ) AS deleted

        FROM messages
    """).fetchone()

    conn.close()

    return row


# ============================================================
# TIME
# ============================================================

def get_timezone(zone_name: str):

    try:

        return ZoneInfo(zone_name)

    except ZoneInfoNotFoundError:

        if zone_name.upper().startswith("UTC"):

            value = zone_name.upper().replace(
                "UTC",
                ""
            )

            try:

                hours = int(value)

                return timezone(
                    timedelta(hours=hours)
                )

            except ValueError:
                pass

    return ZoneInfo("Europe/Moscow")


def get_time_string(settings):

    tz = get_timezone(
        settings["timezone"]
    )

    now = datetime.now(tz)

    if settings["time_format"] == "12":

        if settings["seconds"]:

            return (
                now.strftime("%I:%M:%S %p")
                .lstrip("0")
            )

        return (
            now.strftime("%I:%M %p")
            .lstrip("0")
        )

    if settings["seconds"]:

        return now.strftime("%H:%M:%S")

    return now.strftime("%H:%M")


def timezone_name(zone):

    for _, data in TIMEZONES.items():

        if data[1] == zone:
            return data[0]

    return zone


async def update_business_name(
    connection_id: str,
):

    connection = get_connection(
        connection_id
    )

    if not connection:
        return

    settings = get_settings(
        connection_id
    )

    if not settings["time_enabled"]:
        return

    if not connection["can_edit_name"]:
        return

    current_time = get_time_string(
        settings
    )

    if settings["last_time"] == current_time:
        return

    name = (
        connection["first_name"]
        or "Business"
    )

    if settings["time_position"] == "before":

        new_name = (
            f"{current_time} | {name}"
        )

    else:

        new_name = (
            f"{name} | {current_time}"
        )

    try:

        await bot.set_business_account_name(
            business_connection_id=connection_id,
            first_name=new_name[:64],
            last_name=connection["last_name"],
        )

        update_setting(
            connection_id,
            "last_time",
            current_time,
        )

    except Exception as error:

        logging.warning(
            "Name update error: %s",
            error,
        )


async def time_worker():

    while True:

        try:

            conn = db()

            rows = conn.execute("""
                SELECT connection_id
                FROM settings
                WHERE time_enabled = 1
            """).fetchall()

            conn.close()

            for row in rows:

                await update_business_name(
                    row["connection_id"]
                )

        except Exception:

            logging.exception(
                "Time worker error"
            )

        await asyncio.sleep(15)


# ============================================================
# KEYBOARDS
# ============================================================

def settings_keyboard(connection_id):

    settings = get_settings(
        connection_id
    )

    time_status = (
        "Вкл."
        if settings["time_enabled"]
        else "Выкл."
    )

    style = settings["message_style"]

    style_names = {
        "off": "Выкл.",
        "bold": "Жирный",
        "italic": "Курсив",
        "mono": "Моно",
        "quote": "Цитата",
    }

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🕐 Время в имени: {time_status}",
                    callback_data="settings_time",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💬 Сообщения: {style_names.get(style, 'Выкл.')}",
                    callback_data="settings_messages",
                )
            ],
        ]
    )


def time_keyboard(settings):

    status = (
        "Выключить"
        if settings["time_enabled"]
        else "Включить"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🕐 {status}",
                    callback_data="time_toggle",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌍 Часовой пояс",
                    callback_data="time_timezone",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Формат времени",
                    callback_data="time_format",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📍 Расположение",
                    callback_data="time_position",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔢 Секунды",
                    callback_data="time_seconds",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="settings_main",
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
                callback_data=f"tz_{key}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="✏️ Свой часовой пояс",
            callback_data="tz_custom",
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="settings_time",
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def message_style_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Выключено",
                    callback_data="style_off",
                )
            ],
            [
                InlineKeyboardButton(
                    text="𝐀 Жирный",
                    callback_data="style_bold",
                )
            ],
            [
                InlineKeyboardButton(
                    text="𝘈 Курсив",
                    callback_data="style_italic",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Моноширинный",
                    callback_data="style_mono",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Цитата",
                    callback_data="style_quote",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="settings_main",
                )
            ],
        ]
    )


# ============================================================
# /START
# ВАЖНО: ОБРАБОТЧИК РАНЬШЕ ОБЩЕГО TEXT HANDLER
# ============================================================

@dp.message(
    Command("start"),
    F.chat.type == "private",
)
async def command_start(message: Message):

    if not message.from_user:
        return

    user_id = message.from_user.id

    if user_id == OWNER_ID:

        text = (
            "🤖 bobmod TEST v0.3\n\n"

            "Business-бот запущен.\n\n"

            "Доступно:\n"
            "/settings — настройки\n"
            "/stats — статистика\n\n"

            "В Business-чатах:\n"
            ".help\n"
            ".info\n"
            ".ping"
        )

        await send_custom(
            message.chat.id,
            text,
        )

        return

    if user_id in TESTER_IDS:

        text = (
            "🤖 bobmod TEST v0.3\n\n"

            "🧪 Ты тестер.\n\n"

            "Доступно:\n"
            "/settings — настройки\n\n"

            "В Business-чатах:\n"
            ".help\n"
            ".info\n"
            ".ping\n\n"

            "📊 /stats доступна только владельцу."
        )

        await send_custom(
            message.chat.id,
            text,
        )

        return

    text = (
        "🤖 bobmod TEST v0.3\n\n"

        "Подключи Business-аккаунт "
        "через Автоматизацию чатов."
    )

    await send_custom(
        message.chat.id,
        text,
    )


# ============================================================
# /STATS
# ============================================================

@dp.message(
    Command("stats"),
    F.chat.type == "private",
)
async def command_stats(message: Message):

    if not message.from_user:
        return

    if message.from_user.id != OWNER_ID:

        await send_custom(
            message.chat.id,
            "❌ Эта команда доступна только владельцу.",
        )

        return

    stats = get_stats()

    text = (
        "📊 bobmod TEST v0.3\n\n"

        f"💬 Сообщений: {stats['total']}\n"
        f"✏️ Редактировано: {stats['edited']}\n"
        f"🗑️ Удалено: {stats['deleted']}"
    )

    await send_custom(
        message.chat.id,
        text,
    )


# ============================================================
# /SETTINGS
# ============================================================

@dp.message(
    Command("settings"),
    F.chat.type == "private",
)
async def command_settings(message: Message):

    if not message.from_user:
        return

    connection = get_user_connection(
        message.from_user.id
    )

    if not connection:

        await send_custom(
            message.chat.id,
            "❌ Активное Business-подключение не найдено.",
        )

        return

    settings = get_settings(
        connection["connection_id"]
    )

    text = (
        "🤖 bobmod TEST v0.3\n\n"
        "⚙️ Настройки"
    )

    await bot.send_message(
        chat_id=message.chat.id,
        text=text,
        entities=custom_emoji_entities(text),
        reply_markup=settings_keyboard(
            connection["connection_id"]
        ),
    )


# ============================================================
# BUSINESS CONNECTION
# ============================================================

@dp.business_connection()
async def business_connection_handler(
    connection: BusinessConnection,
):

    save_business_connection(
        connection
    )

    logging.info(
        "Business connection: %s | owner=%s",
        connection.id,
        connection.user.id,
    )


# ============================================================
# SETTINGS MAIN
# ============================================================

@dp.callback_query(
    F.data == "settings_main"
)
async def settings_main(callback: CallbackQuery):

    connection = get_user_connection(
        callback.from_user.id
    )

    if not connection:

        await callback.answer(
            "Business-подключение не найдено.",
            show_alert=True,
        )

        return

    text = (
        "🤖 bobmod TEST v0.3\n\n"
        "⚙️ Настройки"
    )

    await callback.message.edit_text(
        text=text,
        entities=custom_emoji_entities(text),
        reply_markup=settings_keyboard(
            connection["connection_id"]
        ),
    )

    await callback.answer()


# ============================================================
# TIME SETTINGS
# ============================================================

@dp.callback_query(
    F.data == "settings_time"
)
async def settings_time(callback: CallbackQuery):

    connection = get_user_connection(
        callback.from_user.id
    )

    if not connection:

        await callback.answer(
            "Подключение не найдено.",
            show_alert=True,
        )

        return

    settings = get_settings(
        connection["connection_id"]
    )

    enabled = (
        "Включено"
        if settings["time_enabled"]
        else "Выключено"
    )

    permission = (
        "Есть"
        if connection["can_edit_name"]
        else "Нет"
    )

    text = (
        "🕐 Время в имени\n\n"

        f"Статус: {enabled}\n"
        f"🌍 Часовой пояс: {timezone_name(settings['timezone'])}\n"
        f"📝 Формат: {settings['time_format']} часа\n\n"

        f"Разрешение на изменение имени: {permission}\n\n"

        "⚠️ Для работы нужно разрешить bobmod "
        "изменять имя Business-аккаунта."
    )

    await callback.message.edit_text(
        text=text,
        entities=custom_emoji_entities(text),
        reply_markup=time_keyboard(settings),
    )

    await callback.answer()


# ============================================================
# TIME TOGGLE
# ============================================================

@dp.callback_query(
    F.data == "time_toggle"
)
async def time_toggle(callback: CallbackQuery):

    connection = get_user_connection(
        callback.from_user.id
    )

    if not connection:

        return

    if not connection["can_edit_name"]:

        await callback.answer(
            "Нет разрешения на изменение имени.",
            show_alert=True,
        )

        return

    settings = get_settings(
        connection["connection_id"]
    )

    new_value = 0 if settings["time_enabled"] else 1

    update_setting(
        connection["connection_id"],
        "time_enabled",
        new_value,
    )

    update_setting(
        connection["connection_id"],
        "last_time",
        None,
    )

    if new_value:

        await update_business_name(
            connection["connection_id"]
        )

    else:

        try:

            await bot.set_business_account_name(
                business_connection_id=connection["connection_id"],
                first_name=connection["first_name"],
                last_name=connection["last_name"],
            )

        except Exception as error:

            logging.warning(
                "Restore name error: %s",
                error,
            )

    await callback.answer(
        "Настройка обновлена."
    )

    await settings_time(callback)


# ============================================================
# TIMEZONE MENU
# ============================================================

@dp.callback_query(
    F.data == "time_timezone"
)
async def time_timezone(callback: CallbackQuery):

    await callback.message.edit_text(
        text=(
            "🌍 Выбери часовой пояс.\n\n"
            "Также можно указать свой."
        ),
        entities=custom_emoji_entities(
            "🌍 Выбери часовой пояс.\n\n"
            "Также можно указать свой."
        ),
        reply_markup=timezone_keyboard(),
    )

    await callback.answer()


# ============================================================
# TIMEZONE SELECT
# ============================================================

@dp.callback_query(
    F.data.startswith("tz_"),
    F.data != "tz_custom",
)
async def timezone_select(callback: CallbackQuery):

    key = callback.data.replace(
        "tz_",
        "",
        1
    )

    if key not in TIMEZONES:

        await callback.answer(
            "Неизвестный часовой пояс.",
            show_alert=True,
        )

        return

    connection = get_user_connection(
        callback.from_user.id
    )

    if not connection:
        return

    update_setting(
        connection["connection_id"],
        "timezone",
        TIMEZONES[key][1],
    )

    update_setting(
        connection["connection_id"],
        "last_time",
        None,
    )

    await update_business_name(
        connection["connection_id"]
    )

    await callback.answer(
        "Часовой пояс сохранён."
    )

    await settings_time(callback)


# ============================================================
# CUSTOM TIMEZONE
# ============================================================

WAITING_TIMEZONE = set()


@dp.callback_query(
    F.data == "tz_custom"
)
async def custom_timezone(callback: CallbackQuery):

    WAITING_TIMEZONE.add(
        callback.from_user.id
    )

    text = (
        "✏️ Отправь свой часовой пояс.\n\n"

        "Примеры:\n"
        "Europe/Moscow\n"
        "Asia/Almaty\n"
        "America/New_York"
    )

    await callback.message.edit_text(
        text=text,
        entities=custom_emoji_entities(text),
    )

    await callback.answer()


# ============================================================
# FORMAT MENU
# ============================================================

@dp.callback_query(
    F.data == "time_format"
)
async def format_menu(callback: CallbackQuery):

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="15:31",
                    callback_data="format_24",
                )
            ],
            [
                InlineKeyboardButton(
                    text="3:31 PM",
                    callback_data="format_12",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="settings_time",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        "📝 Выбери формат времени.",
        entities=custom_emoji_entities(
            "📝 Выбери формат времени."
        ),
        reply_markup=keyboard,
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("format_")
)
async def format_select(callback: CallbackQuery):

    value = callback.data.replace(
        "format_",
        ""
    )

    if value not in ("12", "24"):
        return

    connection = get_user_connection(
        callback.from_user.id
    )

    if not connection:
        return

    update_setting(
        connection["connection_id"],
        "time_format",
        value,
    )

    update_setting(
        connection["connection_id"],
        "last_time",
        None,
    )

    await update_business_name(
        connection["connection_id"]
    )

    await callback.answer(
        "Формат сохранён."
    )

    await settings_time(callback)


# ============================================================
# POSITION
# ============================================================

@dp.callback_query(
    F.data == "time_position"
)
async def position_menu(callback: CallbackQuery):

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Имя | 15:31",
                    callback_data="position_after",
                )
            ],
            [
                InlineKeyboardButton(
                    text="15:31 | Имя",
                    callback_data="position_before",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="settings_time",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        "📍 Выбери расположение времени.",
        entities=custom_emoji_entities(
            "📍 Выбери расположение времени."
        ),
        reply_markup=keyboard,
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("position_")
)
async def position_select(callback: CallbackQuery):

    value = callback.data.replace(
        "position_",
        ""
    )

    if value not in ("before", "after"):
        return

    connection = get_user_connection(
        callback.from_user.id
    )

    if not connection:
        return

    update_setting(
        connection["connection_id"],
        "time_position",
        value,
    )

    update_setting(
        connection["connection_id"],
        "last_time",
        None,
    )

    await update_business_name(
        connection["connection_id"]
    )

    await callback.answer(
        "Сохранено."
    )

    await settings_time(callback)


# ============================================================
# SECONDS
# ============================================================

@dp.callback_query(
    F.data == "time_seconds"
)
async def seconds_toggle(callback: CallbackQuery):

    connection = get_user_connection(
        callback.from_user.id
    )

    if not connection:
        return

    settings = get_settings(
        connection["connection_id"]
    )

    value = 0 if settings["seconds"] else 1

    update_setting(
        connection["connection_id"],
        "seconds",
        value,
    )

    update_setting(
        connection["connection_id"],
        "last_time",
        None,
    )

    await update_business_name(
        connection["connection_id"]
    )

    await callback.answer(
        "Настройка секунд обновлена."
    )

    await settings_time(callback)


# ============================================================
# MESSAGE STYLE SETTINGS
# ============================================================

@dp.callback_query(
    F.data == "settings_messages"
)
async def settings_messages(callback: CallbackQuery):

    text = (
        "💬 Настройки сообщений\n\n"

        "Выбери стиль, который будет автоматически "
        "применяться к твоим новым текстовым сообщениям."
    )

    await callback.message.edit_text(
        text=text,
        entities=custom_emoji_entities(text),
        reply_markup=message_style_keyboard(),
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("style_")
)
async def style_select(callback: CallbackQuery):

    style = callback.data.replace(
        "style_",
        ""
    )

    allowed = {
        "off",
        "bold",
        "italic",
        "mono",
        "quote",
    }

    if style not in allowed:
        return

    connection = get_user_connection(
        callback.from_user.id
    )

    if not connection:
        return

    update_setting(
        connection["connection_id"],
        "message_style",
        style,
    )

    await callback.answer(
        "Стиль сохранён."
    )

    await settings_messages(callback)


# ============================================================
# BUSINESS COMMAND RESULT
# ============================================================

async def edit_or_replace(
    message: Message,
    connection_id: str,
    text: str,
):

    entities = custom_emoji_entities(text)

    try:

        await bot.edit_message_text(
            business_connection_id=connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=text,
            entities=entities,
        )

        return

    except Exception as error:

        logging.warning(
            "Edit failed: %s",
            error,
        )

    try:

        await bot.send_message(
            business_connection_id=connection_id,
            chat_id=message.chat.id,
            text=text,
            entities=entities,
        )

    except Exception:

        logging.exception(
            "Fallback send failed"
        )

        return

    try:

        await bot.delete_business_messages(
            business_connection_id=connection_id,
            chat_id=message.chat.id,
            message_ids=[
                message.message_id
            ],
        )

    except Exception as error:

        logging.warning(
            "Delete command failed: %s",
            error,
        )


# ============================================================
# MESSAGE STYLE ENTITIES
# ============================================================

def style_entities(text, style):

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


# ============================================================
# BUSINESS MESSAGE
# ============================================================

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

    connection = get_connection(
        connection_id
    )

    if not connection:
        return


    # --------------------------------------------------------
    # SAVE MESSAGE
    # --------------------------------------------------------

    sender_id = None
    sender_name = None
    sender_username = None

    if message.from_user:

        sender_id = message.from_user.id

        sender_name = " ".join(
            x for x in [
                message.from_user.first_name,
                message.from_user.last_name,
            ]
            if x
        )

        sender_username = (
            message.from_user.username
        )


    media_type = None
    file_id = None

    if message.photo:

        media_type = "photo"

        file_id = (
            message.photo[-1].file_id
        )

    elif message.video:

        media_type = "video"

        file_id = message.video.file_id

    elif message.document:

        media_type = "document"

        file_id = message.document.file_id

    elif message.audio:

        media_type = "audio"

        file_id = message.audio.file_id

    elif message.voice:

        media_type = "voice"

        file_id = message.voice.file_id

    elif message.sticker:

        media_type = "sticker"

        file_id = message.sticker.file_id


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
        file_id=file_id,

        created_at=message.date.isoformat(),
    )


    # --------------------------------------------------------
    # BUSINESS COMMANDS
    # --------------------------------------------------------

    if message.text:

        command = (
            message.text
            .strip()
            .lower()
        )


        # .help
        if command == ".help":

            text = (
                "🤖 bobmod TEST\n\n"

                "Доступные команды:\n\n"

                ".help — помощь\n"
                ".info — информация о собеседнике\n"
                ".ping — проверка работы"
            )

            await edit_or_replace(
                message,
                connection_id,
                text,
            )

            return


        # .ping
        if command == ".ping":

            text = (
                "🏓 Pong!\n\n"
                "🤖 bobmod работает."
            )

            await edit_or_replace(
                message,
                connection_id,
                text,
            )

            return


        # .info
        if command == ".info":

            chat = message.chat

            name = " ".join(
                x for x in [
                    chat.first_name,
                    chat.last_name,
                ]
                if x
            )

            if not name:
                name = "Не указано"

            username = (
                f"@{chat.username}"
                if chat.username
                else "Не указан"
            )

            text = (
                "👤 Информация о пользователе\n\n"

                f"🆔 ID: {chat.id}\n"
                f"👤 Имя: {name}\n"
                f"🔗 Username: {username}"
            )

            await edit_or_replace(
                message,
                connection_id,
                text,
            )

            return


    # --------------------------------------------------------
    # MESSAGE AUTO FORMAT
    # --------------------------------------------------------

    if not message.from_user:
        return

    # Форматируем только сообщения владельца Business.
    if message.from_user.id != connection["owner_id"]:
        return

    if not message.text:
        return

    # Команды не форматируем.
    if message.text.startswith("."):
        return

    if message.text.startswith("/"):
        return

    settings = get_settings(
        connection_id
    )

    style = settings["message_style"]

    if style == "off":
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

    except Exception as error:

        logging.warning(
            "Auto format failed: %s",
            error,
        )


# ============================================================
# EDITED BUSINESS MESSAGE
# ============================================================

@dp.edited_business_message()
async def edited_business_message(
    message: Message,
):

    connection_id = (
        message.business_connection_id
    )

    if not connection_id:
        return

    row = get_saved_message(
        connection_id,
        message.chat.id,
        message.message_id,
    )

    if not row:
        return

    original = (
        row["text"]
        or row["caption"]
        or f"[Медиа: {row['media_type']}]"
        or "[Без текста]"
    )

    sender_name = (
        row["sender_name"]
        or "Неизвестно"
    )

    sender_id = (
        row["sender_id"]
        or "Неизвестно"
    )

    text = (
        "✏️ Сообщение отредактировано\n\n"

        f"👤 Отправитель: {sender_name}\n"
        f"🆔 ID: {sender_id}\n\n"

        f"Исходное сообщение:\n{original}"
    )

    try:

        await send_custom(
            OWNER_ID,
            text,
        )

    except Exception:

        logging.exception(
            "Edit notification failed"
        )

    mark_edited(
        connection_id,
        message.chat.id,
        message.message_id,
    )


# ============================================================
# DELETED BUSINESS MESSAGES
# ============================================================

@dp.deleted_business_messages()
async def deleted_business_messages(
    deleted: BusinessMessagesDeleted,
):

    connection_id = (
        deleted.business_connection_id
    )

    if not connection_id:
        return

    for message_id in deleted.message_ids:

        row = get_saved_message(
            connection_id,
            deleted.chat.id,
            message_id,
        )

        if not row:
            continue

        original = (
            row["text"]
            or row["caption"]
            or f"[Медиа: {row['media_type']}]"
            or "[Без текста]"
        )

        sender_name = (
            row["sender_name"]
            or "Неизвестно"
        )

        sender_id = (
            row["sender_id"]
            or "Неизвестно"
        )

        text = (
            "🗑️ Сообщение удалено\n\n"

            f"👤 Отправитель: {sender_name}\n"
            f"🆔 ID: {sender_id}\n\n"

            f"Исходное сообщение:\n{original}"
        )

        try:

            await send_custom(
                OWNER_ID,
                text,
            )

        except Exception:

            logging.exception(
                "Delete notification failed"
            )

        mark_deleted(
            connection_id,
            deleted.chat.id,
            message_id,
        )


# ============================================================
# CUSTOM TIMEZONE INPUT
#
# ВАЖНО:
# Этот handler расположен ПОСЛЕ /start, /stats и /settings,
# поэтому команды больше не перехватываются.
# ============================================================

@dp.message(
    F.chat.type == "private",
    F.text,
    ~F.text.startswith("/"),
)
async def private_text_handler(
    message: Message,
):

    if not message.from_user:
        return

    user_id = message.from_user.id

    if user_id not in WAITING_TIMEZONE:
        return

    zone_name = message.text.strip()

    try:

        ZoneInfo(zone_name)

    except ZoneInfoNotFoundError:

        await send_custom(
            message.chat.id,
            (
                "❌ Такой часовой пояс не найден.\n\n"

                "Примеры:\n"
                "Europe/Moscow\n"
                "Asia/Almaty\n"
                "America/New_York"
            ),
        )

        return


    connection = get_user_connection(
        user_id
    )

    if not connection:

        WAITING_TIMEZONE.discard(
            user_id
        )

        return


    update_setting(
        connection["connection_id"],
        "timezone",
        zone_name,
    )

    update_setting(
        connection["connection_id"],
        "last_time",
        None,
    )

    WAITING_TIMEZONE.discard(
        user_id
    )

    await update_business_name(
        connection["connection_id"]
    )

    await send_custom(
        message.chat.id,
        f"✅ Часовой пояс сохранён: {zone_name}",
    )


# ============================================================
# START
# ============================================================

async def main():

    init_db()

    logging.info(
        "bobmod TEST v0.3 starting..."
    )

    worker = asyncio.create_task(
        time_worker()
    )

    try:

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )

    finally:

        worker.cancel()

        try:

            await worker

        except asyncio.CancelledError:
            pass

        await bot.session.close()


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        logging.info(
            "bobmod stopped"
        )

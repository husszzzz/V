import os
import json
import sqlite3
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify

app = Flask(__name__)

# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

STORE_NAME = os.getenv("STORE_NAME", "بوت الرشق")

# Vercel filesystem مؤقت
DB_PATH = "/tmp/rashq.db"

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# =========================================================
# CUSTOM EMOJIS
# =========================================================

CUSTOM_EMOJIS = {
    "📉": "5429518319243775957",
    "↗️": "5429651785352501917",
    "🛫": "5201691993775818138",
    "⛏": "5197371802136892976",
    "📥": "5443127283898405358",
    "💳": "5445353829304387411",
    "🪣": "5399909394525737759",
    "🛡": "5197288647275071607",
    "🗓": "5274055917766202507",
    "🛍": "5278702045883292456",
    "🎁": "6012722500914386151",
    "👑": "5803032306213982905",
    "🏅": "5803357151770449172",
    "💥": "5802910664150226061",
}


# =========================================================
# DATABASE
# =========================================================

def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    connection = db()
    cur = connection.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance REAL DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s','now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '🛍',
            enabled INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL DEFAULT 0,
            min_amount INTEGER DEFAULT 1,
            max_amount INTEGER DEFAULT 100000,
            enabled INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_id INTEGER,
            target TEXT,
            quantity INTEGER,
            total REAL,
            status TEXT DEFAULT 'pending',
            created_at INTEGER DEFAULT (strftime('%s','now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # أقسام افتراضية
    count = cur.execute(
        "SELECT COUNT(*) FROM sections"
    ).fetchone()[0]

    if count == 0:

        default_sections = [
            ("متابعين", "👥"),
            ("مشاهدات", "📉"),
            ("تفاعلات", "💥"),
            ("إعجابات", "🏅")
        ]

        cur.executemany(
            "INSERT INTO sections (name, emoji) VALUES (?, ?)",
            default_sections
        )

    connection.commit()
    connection.close()


init_db()


# =========================================================
# TELEGRAM API
# =========================================================

def telegram(method, data=None):

    if not BOT_TOKEN:
        return {
            "ok": False,
            "description": "BOT_TOKEN غير موجود"
        }

    data = data or {}

    try:

        encoded = urllib.parse.urlencode(
            data
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{API_URL}/{method}",
            data=encoded,
            headers={
                "Content-Type":
                "application/x-www-form-urlencoded"
            },
            method="POST"
        )

        with urllib.request.urlopen(
            req,
            timeout=20
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except Exception as e:

        print("TELEGRAM ERROR:", e)

        return {
            "ok": False,
            "description": str(e)
        }


# =========================================================
# CUSTOM EMOJI TEXT
# =========================================================

def utf16_length(text):
    return len(
        text.encode("utf-16-le")
    ) // 2


def custom_text(text):

    entities = []

    for emoji, emoji_id in sorted(
        CUSTOM_EMOJIS.items(),
        key=lambda x: len(x[0]),
        reverse=True
    ):

        start = 0

        while True:

            position = text.find(
                emoji,
                start
            )

            if position == -1:
                break

            prefix = text[:position]

            entities.append({
                "offset": utf16_length(prefix),
                "length": utf16_length(emoji),
                "type": "custom_emoji",
                "custom_emoji_id": emoji_id
            })

            start = position + len(emoji)

    return text, entities


# =========================================================
# BUTTON HELPERS
# =========================================================

def button(
    text,
    callback=None,
    style=None,
    emoji_id=None
):

    item = {
        "text": text
    }

    if callback:
        item["callback_data"] = callback

    if style:
        item["style"] = style

    if emoji_id:
        item["icon_custom_emoji_id"] = emoji_id

    return item


# =========================================================
# SEND MESSAGE
# =========================================================

def send_message(
    chat_id,
    text,
    keyboard=None
):

    text, entities = custom_text(text)

    data = {
        "chat_id": chat_id,
        "text": text,
        "entities": json.dumps(
            entities,
            ensure_ascii=False
        )
    }

    if keyboard:
        data["reply_markup"] = json.dumps(
            keyboard,
            ensure_ascii=False
        )

    return telegram(
        "sendMessage",
        data
    )


# =========================================================
# EDIT MESSAGE
# =========================================================

def edit_message(
    chat_id,
    message_id,
    text,
    keyboard=None
):

    text, entities = custom_text(text)

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "entities": json.dumps(
            entities,
            ensure_ascii=False
        )
    }

    if keyboard:

        data["reply_markup"] = json.dumps(
            keyboard,
            ensure_ascii=False
        )

    else:

        data["reply_markup"] = json.dumps(
            {
                "inline_keyboard": []
            }
        )

    result = telegram(
        "editMessageText",
        data
    )

    return result


# =========================================================
# CALLBACK ANSWER
# =========================================================

def answer_callback(
    callback_id,
    text=""
):

    return telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id,
            "text": text
        }
    )


# =========================================================
# USER
# =========================================================

def save_user(user):

    connection = db()

    connection.execute("""
        INSERT INTO users
        (id, username, first_name)
        VALUES (?, ?, ?)

        ON CONFLICT(id)
        DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
    """, (
        user["id"],
        user.get("username", ""),
        user.get("first_name", "")
    ))

    connection.commit()
    connection.close()


def get_user(user_id):

    connection = db()

    row = connection.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    connection.close()

    return row


def change_balance(
    user_id,
    amount
):

    connection = db()

    connection.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE id=?
        """,
        (
            amount,
            user_id
        )
    )

    connection.commit()
    connection.close()


# =========================================================
# MAIN MENU
# =========================================================

def main_keyboard():

    return {
        "inline_keyboard": [

            [
                button(
                    "🛍 الخدمات",
                    "sections",
                    "primary",
                    CUSTOM_EMOJIS["🛍"]
                ),

                button(
                    "👑 حسابي",
                    "account",
                    "primary",
                    CUSTOM_EMOJIS["👑"]
                )
            ],

            [
                button(
                    "💳 شحن الرصيد",
                    "topup",
                    "success",
                    CUSTOM_EMOJIS["💳"]
                ),

                button(
                    "🗓 طلباتي",
                    "orders",
                    "primary",
                    CUSTOM_EMOJIS["🗓"]
                )
            ],

            [
                button(
                    "📉 الإحصائيات",
                    "stats",
                    "primary",
                    CUSTOM_EMOJIS["📉"]
                ),

                button(
                    "🛡 الدعم",
                    "support",
                    "primary",
                    CUSTOM_EMOJIS["🛡"]
                )
            ]

        ]
    }


# =========================================================
# ADMIN MENU
# =========================================================

def admin_keyboard():

    return {
        "inline_keyboard": [

            [
                button(
                    "🛍 إدارة الأقسام",
                    "admin_sections",
                    "primary",
                    CUSTOM_EMOJIS["🛍"]
                )
            ],

            [
                button(
                    "📦 إدارة الخدمات",
                    "admin_services",
                    "primary",
                    CUSTOM_EMOJIS["📥"]
                )
            ],

            [
                button(
                    "🗓 الطلبات المعلقة",
                    "admin_orders",
                    "primary",
                    CUSTOM_EMOJIS["🗓"]
                )
            ],

            [
                button(
                    "📊 إحصائيات المتجر",
                    "admin_stats",
                    "primary",
                    CUSTOM_EMOJIS["📉"]
                )
            ],

            [
                button(
                    "🔙 الرئيسية",
                    "home",
                    "danger"
                )
            ]

        ]
    }


# =========================================================
# START
# =========================================================

def start_user(
    chat_id,
    user,
    message_id=None
):

    save_user(user)

    row = get_user(
        user["id"]
    )

    balance = (
        row["balance"]
        if row
        else 0
    )

    text = f"""
👑 أهلاً بك في {STORE_NAME}

🛍 منصة خدمات رقمية سريعة ومرتبة

💳 رصيدك الحالي:
{balance:.1f} نقطة

✨ اختر العملية المطلوبة من الأسفل.
""".strip()

    keyboard = main_keyboard()

    if message_id:

        edit_message(
            chat_id,
            message_id,
            text,
            keyboard
        )

    else:

        send_message(
            chat_id,
            text,
            keyboard
        )


# =========================================================
# SECTIONS
# =========================================================

def show_sections(
    chat_id,
    message_id
):

    connection = db()

    rows = connection.execute("""
        SELECT *
        FROM sections
        WHERE enabled=1
        ORDER BY id ASC
    """).fetchall()

    connection.close()

    buttons = []

    for row in rows:

        buttons.append([
            button(
                f"{row['emoji']} {row['name']}",
                f"section:{row['id']}",
                "primary"
            )
        ])

    buttons.append([
        button(
            "🔙 الرئيسية",
            "home",
            "danger"
        )
    ])

    edit_message(
        chat_id,
        message_id,
        "🛍 الأقسام\n\nاختر القسم المطلوب:",
        {
            "inline_keyboard": buttons
        }
    )


# =========================================================
# SERVICES
# =========================================================

def show_services(
    chat_id,
    message_id,
    section_id
):

    connection = db()

    section = connection.execute(
        "SELECT * FROM sections WHERE id=?",
        (section_id,)
    ).fetchone()

    rows = connection.execute(
        """
        SELECT *
        FROM services
        WHERE section_id=?
        AND enabled=1
        ORDER BY id ASC
        """,
        (section_id,)
    ).fetchall()

    connection.close()

    if not section:

        edit_message(
            chat_id,
            message_id,
            "❌ القسم غير موجود.",
            {
                "inline_keyboard": [
                    [
                        button(
                            "🔙 الأقسام",
                            "sections",
                            "danger"
                        )
                    ]
                ]
            }
        )

        return

    buttons = []

    for row in rows:

        buttons.append([
            button(
                f"🛍 {row['name']} — {row['price']} نقطة",
                f"service:{row['id']}",
                "primary"
            )
        ])

    buttons.append([
        button(
            "🔙 الأقسام",
            "sections",
            "danger"
        )
    ])

    edit_message(
        chat_id,
        message_id,
        f"{section['emoji']} {section['name']}\n\nاختر الخدمة المطلوبة:",
        {
            "inline_keyboard": buttons
        }
    )


# =========================================================
# SERVICE DETAILS
# =========================================================

def show_service(
    chat_id,
    message_id,
    service_id
):

    connection = db()

    row = connection.execute(
        """
        SELECT *
        FROM services
        WHERE id=?
        AND enabled=1
        """,
        (service_id,)
    ).fetchone()

    connection.close()

    if not row:

        edit_message(
            chat_id,
            message_id,
            "❌ الخدمة غير موجودة."
        )

        return

    text = f"""
🛍 {row['name']}

📝 {row['description'] or 'لا يوجد وصف'}

💰 السعر:
{row['price']} نقطة لكل 1000

📊 الحد الأدنى:
{row['min_amount']}

📊 الحد الأقصى:
{row['max_amount']}

✨ اضغط بالأسفل للمتابعة.
""".strip()

    keyboard = {
        "inline_keyboard": [

            [
                button(
                    "🛒 طلب الخدمة",
                    f"order:{row['id']}",
                    "success"
                )
            ],

            [
                button(
                    "🔙 رجوع",
                    f"section:{row['section_id']}",
                    "danger"
                )
            ]

        ]
    }

    edit_message(
        chat_id,
        message_id,
        text,
        keyboard
    )


# =========================================================
# ACCOUNT
# =========================================================

def show_account(
    chat_id,
    message_id,
    user_id
):

    user = get_user(user_id)

    if not user:
        return

    username = (
        f"@{user['username']}"
        if user["username"]
        else "بدون معرف"
    )

    text = f"""
👑 حسابك

🆔 ID:
{user['id']}

👤 المستخدم:
{username}

💳 الرصيد:
{user['balance']:.1f} نقطة
""".strip()

    keyboard = {
        "inline_keyboard": [

            [
                button(
                    "💳 شحن الرصيد",
                    "topup",
                    "success"
                )
            ],

            [
                button(
                    "🗓 طلباتي",
                    "orders",
                    "primary"
                )
            ],

            [
                button(
                    "🔙 الرئيسية",
                    "home",
                    "danger"
                )
            ]

        ]
    }

    edit_message(
        chat_id,
        message_id,
        text,
        keyboard
    )


# =========================================================
# ORDERS
# =========================================================

def show_orders(
    chat_id,
    message_id,
    user_id
):

    connection = db()

    rows = connection.execute(
        """
        SELECT orders.*, services.name
        FROM orders

        LEFT JOIN services
        ON services.id=orders.service_id

        WHERE orders.user_id=?

        ORDER BY orders.id DESC

        LIMIT 10
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    if not rows:

        text = """
🗓 طلباتك

لا توجد لديك طلبات حتى الآن.
""".strip()

    else:

        status_names = {
            "pending": "⏳ بانتظار المراجعة",
            "accepted": "🔵 مقبول",
            "working": "🛠 قيد التنفيذ",
            "completed": "✅ مكتمل",
            "rejected": "❌ مرفوض"
        }

        text = "🗓 آخر طلباتك\n\n"

        for row in rows:

            status = status_names.get(
                row["status"],
                row["status"]
            )

            text += (
                f"🆔 #{row['id']}\n"
                f"🛍 {row['name']}\n"
                f"📊 {row['quantity']}\n"
                f"{status}\n"
                f"────────────\n"
            )

    edit_message(
        chat_id,
        message_id,
        text,
        {
            "inline_keyboard": [
                [
                    button(
                        "🔄 تحديث",
                        "orders",
                        "primary"
                    )
                ],
                [
                    button(
                        "🔙 الرئيسية",
                        "home",
                        "danger"
                    )
                ]
            ]
        }
    )


# =========================================================
# STATS
# =========================================================

def stats_text():

    connection = db()

    users = connection.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    orders = connection.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0]

    completed = connection.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status='completed'
        """
    ).fetchone()[0]

    pending = connection.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE status='pending'
        """
    ).fetchone()[0]

    connection.close()

    return f"""
📊 إحصائيات المتجر

👥 المستخدمون:
{users}

🗓 جميع الطلبات:
{orders}

⏳ المعلقة:
{pending}

🏅 المكتملة:
{completed}
""".strip()


def show_stats(
    chat_id,
    message_id
):

    edit_message(
        chat_id,
        message_id,
        stats_text(),
        {
            "inline_keyboard": [
                [
                    button(
                        "🔄 تحديث",
                        "stats",
                        "primary"
                    )
                ],
                [
                    button(
                        "🔙 الرئيسية",
                        "home",
                        "danger"
                    )
                ]
            ]
        }
    )


# =========================================================
# SUPPORT
# =========================================================

def show_support(
    chat_id,
    message_id
):

    text = """
🛡 الدعم

إذا واجهتك مشكلة في طلبك أو حسابك،
تواصل مع الإدارة.

✨ سيتم الرد عليك بأقرب وقت.
""".strip()

    edit_message(
        chat_id,
        message_id,
        text,
        {
            "inline_keyboard": [
                [
                    button(
                        "🔙 الرئيسية",
                        "home",
                        "danger"
                    )
                ]
            ]
        }
    )


# =========================================================
# TOPUP
# =========================================================

def create_invoice(
    chat_id,
    message_id
):

    result = telegram(
        "sendInvoice",
        {
            "chat_id": chat_id,
            "title": "💳 شحن الرصيد",
            "description": "شحن 10 نقاط",
            "payload": f"topup_{chat_id}_10",
            "currency": "XTR",
            "prices": json.dumps([
                {
                    "label": "10 نقاط",
                    "amount": 10
                }
            ])
        }
    )

    if result.get("ok"):

        edit_message(
            chat_id,
            message_id,
            """
💳 شحن الرصيد

اخترت باقة الشحن.

✨ سيتم إرسال فاتورة Telegram Stars.
""".strip(),
            {
                "inline_keyboard": [
                    [
                        button(
                            "🔙 الرئيسية",
                            "home",
                            "danger"
                        )
                    ]
                ]
            }
        )

    else:

        edit_message(
            chat_id,
            message_id,
            "❌ تعذر إنشاء فاتورة الشحن حالياً.",
            {
                "inline_keyboard": [
                    [
                        button(
                            "🔙 الرئيسية",
                            "home",
                            "danger"
                        )
                    ]
                ]
            }
        )


# =========================================================
# ADMIN HOME
# =========================================================

def admin_menu(
    chat_id,
    message_id
):

    text = f"""
👑 لوحة تحكم {STORE_NAME}

🛠 من هنا تقدر تدير:

🛍 الأقسام
📦 الخدمات
🗓 الطلبات
📊 الإحصائيات

اختر العملية:
""".strip()

    edit_message(
        chat_id,
        message_id,
        text,
        admin_keyboard()
    )


# =========================================================
# ADMIN SECTIONS
# =========================================================

def admin_sections(
    chat_id,
    message_id
):

    connection = db()

    rows = connection.execute(
        "SELECT * FROM sections ORDER BY id"
    ).fetchall()

    connection.close()

    buttons = []

    for row in rows:

        status = (
            "🟢"
            if row["enabled"]
            else "🔴"
        )

        buttons.append([
            button(
                f"{status} {row['emoji']} {row['name']}",
                f"admin_section:{row['id']}",
                "primary"
            )
        ])

    buttons.append([
        button(
            "➕ إضافة قسم",
            "admin_add_section",
            "success"
        )
    ])

    buttons.append([
        button(
            "🔙 لوحة الإدارة",
            "admin",
            "danger"
        )
    ])

    edit_message(
        chat_id,
        message_id,
        "🛍 إدارة الأقسام\n\nاختر القسم:",
        {
            "inline_keyboard": buttons
        }
    )


# =========================================================
# ADMIN SERVICES
# =========================================================

def admin_services(
    chat_id,
    message_id
):

    connection = db()

    rows = connection.execute(
        """
        SELECT services.*, sections.name AS section_name
        FROM services

        LEFT JOIN sections
        ON sections.id=services.section_id

        ORDER BY services.id DESC

        LIMIT 50
        """
    ).fetchall()

    connection.close()

    buttons = []

    for row in rows:

        status = (
            "🟢"
            if row["enabled"]
            else "🔴"
        )

        buttons.append([
            button(
                f"{status} {row['name']}",
                f"admin_service:{row['id']}",
                "primary"
            )
        ])

    buttons.append([
        button(
            "➕ إضافة خدمة",
            "admin_add_service",
            "success"
        )
    ])

    buttons.append([
        button(
            "🔙 لوحة الإدارة",
            "admin",
            "danger"
        )
    ])

    edit_message(
        chat_id,
        message_id,
        "📦 إدارة الخدمات\n\nاختر الخدمة:",
        {
            "inline_keyboard": buttons
        }
    )


# =========================================================
# ADMIN ORDERS
# =========================================================

def admin_orders(
    chat_id,
    message_id
):

    connection = db()

    rows = connection.execute(
        """
        SELECT orders.*, services.name
        FROM orders

        LEFT JOIN services
        ON services.id=orders.service_id

        WHERE orders.status='pending'

        ORDER BY orders.id DESC

        LIMIT 20
        """
    ).fetchall()

    connection.close()

    if not rows:

        edit_message(
            chat_id,
            message_id,
            "🗓 الطلبات المعلقة\n\n✅ لا توجد طلبات معلقة.",
            {
                "inline_keyboard": [
                    [
                        button(
                            "🔙 لوحة الإدارة",
                            "admin",
                            "danger"
                        )
                    ]
                ]
            }
        )

        return

    text = "🗓 الطلبات المعلقة\n\n"

    buttons = []

    for row in rows:

        text += (
            f"🆔 #{row['id']}\n"
            f"🛍 {row['name']}\n"
            f"🎯 {row['target']}\n"
            f"📊 {row['quantity']}\n"
            f"💰 {row['total']} نقطة\n"
            f"────────────\n"
        )

        buttons.append([
            button(
                f"✅ قبول #{row['id']}",
                f"accept:{row['id']}",
                "success"
            ),
            button(
                f"❌ رفض #{row['id']}",
                f"reject:{row['id']}",
                "danger"
            )
        ])

    buttons.append([
        button(
            "🔙 لوحة الإدارة",
            "admin",
            "danger"
        )
    ])

    edit_message(
        chat_id,
        message_id,
        text,
        {
            "inline_keyboard": buttons
        }
    )


# =========================================================
# ADMIN STATS
# =========================================================

def admin_stats(
    chat_id,
    message_id
):

    edit_message(
        chat_id,
        message_id,
        stats_text(),
        {
            "inline_keyboard": [
                [
                    button(
                        "🔄 تحديث",
                        "admin_stats",
                        "primary"
                    )
                ],
                [
                    button(
                        "🔙 لوحة الإدارة",
                        "admin",
                        "danger"
                    )
                ]
            ]
        }
    )


# =========================================================
# ORDER STATE
# =========================================================

PENDING = {}


def begin_order(
    chat_id,
    message_id,
    service_id,
    user_id
):

    connection = db()

    service = connection.execute(
        "SELECT * FROM services WHERE id=?",
        (service_id,)
    ).fetchone()

    connection.close()

    if not service:
        return

    PENDING[user_id] = {
        "type": "target",
        "service_id": service_id,
        "message_id": message_id
    }

    edit_message(
        chat_id,
        message_id,
        f"""
🛒 إنشاء الطلب

🛍 الخدمة:
{service['name']}

🎯 أرسل الآن الرابط أو المعرف المطلوب.

مثال:
https://t.me/example
""".strip(),
        {
            "inline_keyboard": [
                [
                    button(
                        "❌ إلغاء",
                        "cancel_order",
                        "danger"
                    )
                ]
            ]
        }
    )


def receive_target(
    user_id,
    chat_id,
    text
):

    state = PENDING.get(user_id)

    if not state:
        return False

    connection = db()

    service = connection.execute(
        "SELECT * FROM services WHERE id=?",
        (state["service_id"],)
    ).fetchone()

    connection.close()

    if not service:
        PENDING.pop(user_id, None)
        return True

    state["type"] = "quantity"
    state["target"] = text

    edit_message(
        chat_id,
        state["message_id"],
        f"""
📊 الكمية المطلوبة

🛍 الخدمة:
{service['name']}

📉 الحد الأدنى:
{service['min_amount']}

📈 الحد الأقصى:
{service['max_amount']}

أرسل الكمية فقط.
""".strip(),
        {
            "inline_keyboard": [
                [
                    button(
                        "❌ إلغاء",
                        "cancel_order",
                        "danger"
                    )
                ]
            ]
        }
    )

    return True


def receive_quantity(
    user_id,
    chat_id,
    text
):

    state = PENDING.get(user_id)

    if not state:
        return False

    try:
        quantity = int(text)

    except:

        edit_message(
            chat_id,
            state["message_id"],
            "❌ أرسل رقم الكمية فقط."
        )

        return True

    connection = db()

    service = connection.execute(
        "SELECT * FROM services WHERE id=?",
        (state["service_id"],)
    ).fetchone()

    connection.close()

    if not service:
        PENDING.pop(user_id, None)
        return True

    if quantity < service["min_amount"]:

        edit_message(
            chat_id,
            state["message_id"],
            f"❌ الحد الأدنى هو {service['min_amount']}."
        )

        return True

    if quantity > service["max_amount"]:

        edit_message(
            chat_id,
            state["message_id"],
            f"❌ الحد الأقصى هو {service['max_amount']}."
        )

        return True

    total = (
        quantity / 1000
    ) * service["price"]

    user = get_user(user_id)

    balance = (
        user["balance"]
        if user
        else 0
    )

    if balance < total:

        PENDING.pop(user_id, None)

        edit_message(
            chat_id,
            state["message_id"],
            f"""
❌ الرصيد غير كافٍ.

💳 رصيدك:
{balance:.1f}

💰 المطلوب:
{total:.1f}
""".strip(),
            {
                "inline_keyboard": [
                    [
                        button(
                            "💳 شحن الرصيد",
                            "topup",
                            "success"
                        )
                    ],
                    [
                        button(
                            "🔙 الرئيسية",
                            "home",
                            "danger"
                        )
                    ]
                ]
            }
        )

        return True

    change_balance(
        user_id,
        -total
    )

    connection = db()

    cur = connection.cursor()

    cur.execute(
        """
        INSERT INTO orders
        (
            user_id,
            service_id,
            target,
            quantity,
            total
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            service["id"],
            state["target"],
            quantity,
            total
        )
    )

    order_id = cur.lastrowid

    connection.commit()
    connection.close()

    PENDING.pop(user_id, None)

    edit_message(
        chat_id,
        state["message_id"],
        f"""
✅ تم إنشاء الطلب بنجاح

🆔 رقم الطلب:
#{order_id}

🛍 الخدمة:
{service['name']}

🎯 الهدف:
{state['target']}

📊 الكمية:
{quantity}

💰 التكلفة:
{total:.1f} نقطة

⏳ الحالة:
بانتظار مراجعة الإدارة.
""".strip(),
        {
            "inline_keyboard": [
                [
                    button(
                        "🗓 طلباتي",
                        "orders",
                        "primary"
                    )
                ],
                [
                    button(
                        "🔙 الرئيسية",
                        "home",
                        "danger"
                    )
                ]
            ]
        }
    )

    if ADMIN_ID:

        send_message(
            ADMIN_ID,
            f"""
🚨 طلب جديد

🆔 #{order_id}

👤 المستخدم:
{user_id}

🛍 الخدمة:
{service['name']}

🎯 الهدف:
{state['target']}

📊 الكمية:
{quantity}

💰 التكلفة:
{total:.1f} نقطة
""".strip(),
            {
                "inline_keyboard": [
                    [
                        button(
                            "✅ قبول",
                            f"accept:{order_id}",
                            "success"
                        ),
                        button(
                            "❌ رفض",
                            f"reject:{order_id}",
                            "danger"
                        )
                    ]
                ]
            }
        )

    return True


# =========================================================
# ACCEPT / REJECT
# =========================================================

def accept_order(order_id):

    connection = db()

    row = connection.execute(
        "SELECT * FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()

    if not row:
        connection.close()
        return

    connection.execute(
        """
        UPDATE orders
        SET status='accepted'
        WHERE id=?
        """,
        (order_id,)
    )

    connection.commit()
    connection.close()

    send_message(
        row["user_id"],
        f"✅ تم قبول طلبك #{order_id}\n\n🛠 سيتم البدء بتنفيذ الطلب."
    )


def reject_order(order_id):

    connection = db()

    row = connection.execute(
        "SELECT * FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()

    if not row:
        connection.close()
        return

    if row["status"] == "pending":

        change_balance(
            row["user_id"],
            row["total"]
        )

    connection.execute(
        """
        UPDATE orders
        SET status='rejected'
        WHERE id=?
        """,
        (order_id,)
    )

    connection.commit()
    connection.close()

    send_message(
        row["user_id"],
        f"""
❌ تم رفض طلبك #{order_id}

💳 تم إرجاع:
{row['total']} نقطة
""".strip()
    )


# =========================================================
# CALLBACK
# =========================================================

def handle_callback(callback):

    callback_id = callback["id"]

    data = callback.get(
        "data",
        ""
    )

    message = callback.get(
        "message",
        {}
    )

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get("id")

    message_id = message.get(
        "message_id"
    )

    user = callback.get(
        "from",
        {}
    )

    user_id = user.get(
        "id"
    )

    answer_callback(
        callback_id
    )

    # -------------------------
    # GENERAL
    # -------------------------

    if data == "home":

        start_user(
            chat_id,
            user,
            message_id
        )

        return

    if data == "sections":

        show_sections(
            chat_id,
            message_id
        )

        return

    if data == "account":

        show_account(
            chat_id,
            message_id,
            user_id
        )

        return

    if data == "orders":

        show_orders(
            chat_id,
            message_id,
            user_id
        )

        return

    if data == "stats":

        show_stats(
            chat_id,
            message_id
        )

        return

    if data == "support":

        show_support(
            chat_id,
            message_id
        )

        return

    if data == "topup":

        create_invoice(
            chat_id,
            message_id
        )

        return

    if data == "cancel_order":

        PENDING.pop(
            user_id,
            None
        )

        start_user(
            chat_id,
            user,
            message_id
        )

        return

    # -------------------------
    # SECTIONS
    # -------------------------

    if data.startswith("section:"):

        section_id = int(
            data.split(":")[1]
        )

        show_services(
            chat_id,
            message_id,
            section_id
        )

        return

    # -------------------------
    # SERVICE
    # -------------------------

    if data.startswith("service:"):

        service_id = int(
            data.split(":")[1]
        )

        show_service(
            chat_id,
            message_id,
            service_id
        )

        return

    if data.startswith("order:"):

        service_id = int(
            data.split(":")[1]
        )

        begin_order(
            chat_id,
            message_id,
            service_id,
            user_id
        )

        return

    # -------------------------
    # ADMIN
    # -------------------------

    if user_id != ADMIN_ID:
        return

    if data == "admin":

        admin_menu(
            chat_id,
            message_id
        )

        return

    if data == "admin_sections":

        admin_sections(
            chat_id,
            message_id
        )

        return

    if data == "admin_services":

        admin_services(
            chat_id,
            message_id
        )

        return

    if data == "admin_orders":

        admin_orders(
            chat_id,
            message_id
        )

        return

    if data == "admin_stats":

        admin_stats(
            chat_id,
            message_id
        )

        return

    if data.startswith("accept:"):

        order_id = int(
            data.split(":")[1]
        )

        accept_order(
            order_id
        )

        answer_callback(
            callback_id,
            "✅ تم قبول الطلب"
        )

        return

    if data.startswith("reject:"):

        order_id = int(
            data.split(":")[1]
        )

        reject_order(
            order_id
        )

        answer_callback(
            callback_id,
            "❌ تم رفض الطلب"
        )

        return


# =========================================================
# UPDATE
# =========================================================

def handle_update(update):

    if "callback_query" in update:

        handle_callback(
            update["callback_query"]
        )

        return

    message = update.get(
        "message"
    )

    if not message:
        return

    user = message.get(
        "from",
        {}
    )

    chat = message.get(
        "chat",
        {}
    )

    user_id = user.get(
        "id"
    )

    chat_id = chat.get(
        "id"
    )

    if not user_id or not chat_id:
        return

    save_user(user)

    text = message.get(
        "text",
        ""
    )

    # -------------------------
    # ADMIN
    # -------------------------

    if (
        text == "/admin"
        and user_id == ADMIN_ID
    ):

        # أول مرة نرسل لوحة الإدارة
        send_message(
            chat_id,
            f"""
👑 لوحة تحكم {STORE_NAME}

اختر العملية المطلوبة:
""".strip(),
            admin_keyboard()
        )

        return

    # -------------------------
    # START
    # -------------------------

    if text.startswith("/start"):

        start_user(
            chat_id,
            user
        )

        return

    # -------------------------
    # PENDING ORDER
    # -------------------------

    if user_id in PENDING:

        state = PENDING[user_id]

        if state["type"] == "target":

            receive_target(
                user_id,
                chat_id,
                text
            )

            return

        if state["type"] == "quantity":

            receive_quantity(
                user_id,
                chat_id,
                text
            )

            return

    # -------------------------
    # HELP
    # -------------------------

    if text == "/help":

        send_message(
            chat_id,
            """
🛡 المساعدة

🛍 اختر الخدمة
🎯 أرسل الهدف
📊 أرسل الكمية
💳 تأكد من وجود الرصيد
🗓 تابع طلبك من قسم طلباتي
""".strip(),
            {
                "inline_keyboard": [
                    [
                        button(
                            "🛍 الخدمات",
                            "sections",
                            "primary"
                        )
                    ],
                    [
                        button(
                            "🔙 الرئيسية",
                            "home",
                            "danger"
                        )
                    ]
                ]
            }
        )

        return


# =========================================================
# WEBHOOK
# =========================================================

@app.route(
    "/",
    methods=["GET"]
)
def root():

    return jsonify({
        "ok": True,
        "service": STORE_NAME,
        "status": "online",
        "telegram": "webhook"
    })


@app.route(
    "/",
    methods=["POST"]
)
def webhook():

    try:

        update = request.get_json(
            silent=True
        )

        if not update:

            return jsonify({
                "ok": False,
                "error": "empty update"
            }), 400

        handle_update(
            update
        )

        return jsonify({
            "ok": True
        })

    except Exception as e:

        print(
            "WEBHOOK ERROR:",
            str(e)
        )

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 200


# =========================================================
# HEALTH
# =========================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({
        "ok": True,
        "service": STORE_NAME
    })


# =========================================================
# LOCAL
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8000
    )

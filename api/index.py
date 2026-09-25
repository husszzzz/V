import os
import json
import sqlite3
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify

# =========================================================
# APP
# =========================================================

app = Flask(__name__)

# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
STORE_NAME = os.getenv("STORE_NAME", "بوت الرشق")

# Vercel يسمح بالكتابة المؤقتة داخل /tmp
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

# حالات الطلب المؤقتة
PENDING = {}


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
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
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
            enabled INTEGER DEFAULT 1,
            FOREIGN KEY(section_id) REFERENCES sections(id)
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
        CREATE TABLE IF NOT EXISTS topups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stars INTEGER,
            status TEXT DEFAULT 'pending',
            telegram_charge_id TEXT DEFAULT '',
            created_at INTEGER DEFAULT (strftime('%s','now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # إنشاء الأقسام الافتراضية مرة واحدة
    count = cur.execute(
        "SELECT COUNT(*) FROM sections"
    ).fetchone()[0]

    if count == 0:
        default_sections = [
            ("متابعين", "👥"),
            ("مشاهدات", "📉"),
            ("تفاعلات", "💥"),
            ("إعجابات", "🏅"),
        ]

        for name, emoji in default_sections:
            cur.execute(
                "INSERT INTO sections (name, emoji) VALUES (?, ?)",
                (name, emoji)
            )

    connection.commit()
    connection.close()


try:
    init_db()
except Exception as e:
    print("DATABASE INIT ERROR:", e)


# =========================================================
# TELEGRAM API
# =========================================================

def telegram(method, data=None):
    if not BOT_TOKEN:
        return {
            "ok": False,
            "description": "BOT_TOKEN غير موجود في Vercel"
        }

    data = data or {}

    try:
        encoded = urllib.parse.urlencode(
            data,
            doseq=True
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

            raw = response.read().decode("utf-8")

            return json.loads(raw)

    except Exception as e:
        print("TELEGRAM ERROR:", e)

        return {
            "ok": False,
            "description": str(e)
        }


# =========================================================
# CUSTOM EMOJI HELPERS
# =========================================================

def utf16_length(text):
    return len(
        text.encode("utf-16-le")
    ) // 2


def custom_text(text):
    entities = []

    for emoji, emoji_id in sorted(
        CUSTOM_EMOJIS.items(),
        key=lambda item: len(item[0]),
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

            entities.append({
                "offset": utf16_length(
                    text[:position]
                ),
                "length": utf16_length(
                    emoji
                ),
                "type": "custom_emoji",
                "custom_emoji_id": emoji_id
            })

            start = position + len(emoji)

    return text, entities


# =========================================================
# MESSAGES
# =========================================================

def send_message(
    chat_id,
    text,
    keyboard=None
):
    text, entities = custom_text(text)

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if entities:
        data["entities"] = json.dumps(
            entities,
            ensure_ascii=False
        )

    if keyboard:
        data["reply_markup"] = json.dumps(
            keyboard,
            ensure_ascii=False
        )

    return telegram(
        "sendMessage",
        data
    )


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
# USERS
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
        user.get("id"),
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

    connection.execute("""
        UPDATE users
        SET balance = balance + ?
        WHERE id=?
    """, (
        amount,
        user_id
    ))

    connection.commit()
    connection.close()


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard():
    return {
        "inline_keyboard": [

            [
                {
                    "text": "🛍 الخدمات",
                    "callback_data": "sections"
                },
                {
                    "text": "👑 حسابي",
                    "callback_data": "account"
                }
            ],

            [
                {
                    "text": "💳 شحن الرصيد",
                    "callback_data": "topup"
                },
                {
                    "text": "🗓 طلباتي",
                    "callback_data": "orders"
                }
            ],

            [
                {
                    "text": "📉 الإحصائيات",
                    "callback_data": "stats"
                },
                {
                    "text": "🛡 الدعم",
                    "callback_data": "support"
                }
            ]
        ]
    }


# =========================================================
# ADMIN KEYBOARD
# =========================================================

def admin_keyboard():
    return {
        "inline_keyboard": [

            [
                {
                    "text": "🛍 إدارة الأقسام",
                    "callback_data": "admin_sections"
                }
            ],

            [
                {
                    "text": "📉 إدارة الخدمات",
                    "callback_data": "admin_services"
                }
            ],

            [
                {
                    "text": "🗓 الطلبات المعلقة",
                    "callback_data": "admin_orders"
                }
            ],

            [
                {
                    "text": "📊 الإحصائيات",
                    "callback_data": "admin_stats"
                }
            ]
        ]
    }


# =========================================================
# START
# =========================================================

def start_user(
    chat_id,
    user
):
    save_user(user)

    current = get_user(
        user["id"]
    )

    balance = (
        current["balance"]
        if current
        else 0
    )

    text = f"""
👑 أهلاً بك في {STORE_NAME}

🛍 منصة خدمات رقمية

💳 رصيدك:
{balance} نقطة

✨ اختر العملية المطلوبة:
""".strip()

    send_message(
        chat_id,
        text,
        main_keyboard()
    )


# =========================================================
# SECTIONS
# =========================================================

def show_sections(chat_id):

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
            {
                "text":
                f"{row['emoji']} {row['name']}",

                "callback_data":
                f"section:{row['id']}"
            }
        ])

    buttons.append([
        {
            "text": "🔙 الرئيسية",
            "callback_data": "home"
        }
    ])

    send_message(
        chat_id,
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
    section_id
):

    connection = db()

    rows = connection.execute("""
        SELECT *
        FROM services
        WHERE section_id=?
        AND enabled=1
        ORDER BY id ASC
    """, (
        section_id,
    )).fetchall()

    connection.close()

    buttons = []

    for row in rows:

        buttons.append([
            {
                "text":
                f"🛍 {row['name']} — {row['price']} نقطة",

                "callback_data":
                f"service:{row['id']}"
            }
        ])

    buttons.append([
        {
            "text": "🔙 الأقسام",
            "callback_data": "sections"
        }
    ])

    send_message(
        chat_id,
        "📦 الخدمات المتاحة\n\nاختر الخدمة:",
        {
            "inline_keyboard": buttons
        }
    )


# =========================================================
# SERVICE DETAILS
# =========================================================

def show_service(
    chat_id,
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
        send_message(
            chat_id,
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

اضغط لطلب الخدمة:
""".strip()

    keyboard = {
        "inline_keyboard": [

            [
                {
                    "text": "🛒 طلب الخدمة",
                    "callback_data":
                    f"order:{row['id']}"
                }
            ],

            [
                {
                    "text": "🔙 رجوع",
                    "callback_data":
                    f"section:{row['section_id']}"
                }
            ]
        ]
    }

    send_message(
        chat_id,
        text,
        keyboard
    )


# =========================================================
# BEGIN ORDER
# =========================================================

def begin_order(
    user_id,
    chat_id,
    service_id
):

    connection = db()

    service = connection.execute(
        """
        SELECT *
        FROM services
        WHERE id=?
        AND enabled=1
        """,
        (service_id,)
    ).fetchone()

    connection.close()

    if not service:
        send_message(
            chat_id,
            "❌ الخدمة غير موجودة."
        )
        return

    PENDING[user_id] = {
        "type": "order_target",
        "service_id": service_id
    }

    send_message(
        chat_id,
        f"""
🛒 إنشاء طلب

🛍 الخدمة:
{service['name']}

🎯 أرسل الآن الرابط أو المعرف المطلوب.

مثال:
https://t.me/example
""".strip()
    )


# =========================================================
# RECEIVE TARGET
# =========================================================

def receive_order_target(
    user_id,
    chat_id,
    text
):

    state = PENDING.get(
        user_id
    )

    if not state:
        return False

    service_id = state["service_id"]

    connection = db()

    service = connection.execute(
        "SELECT * FROM services WHERE id=?",
        (service_id,)
    ).fetchone()

    connection.close()

    if not service:
        PENDING.pop(
            user_id,
            None
        )

        send_message(
            chat_id,
            "❌ الخدمة غير موجودة."
        )

        return True

    PENDING[user_id] = {
        "type": "order_quantity",
        "service_id": service_id,
        "target": text.strip()
    }

    send_message(
        chat_id,
        f"""
📊 الكمية المطلوبة

🛍 الخدمة:
{service['name']}

🔽 الحد الأدنى:
{service['min_amount']}

🔼 الحد الأقصى:
{service['max_amount']}

أرسل الكمية فقط.
""".strip()
    )

    return True


# =========================================================
# RECEIVE QUANTITY
# =========================================================

def receive_order_quantity(
    user_id,
    chat_id,
    text
):

    state = PENDING.get(
        user_id
    )

    if not state:
        return False

    try:
        quantity = int(
            text.strip()
        )
    except:
        send_message(
            chat_id,
            "❌ أرسل رقم الكمية فقط."
        )
        return True

    service_id = state["service_id"]

    connection = db()

    service = connection.execute(
        "SELECT * FROM services WHERE id=?",
        (service_id,)
    ).fetchone()

    connection.close()

    if not service:
        PENDING.pop(
            user_id,
            None
        )

        send_message(
            chat_id,
            "❌ الخدمة غير موجودة."
        )

        return True

    if quantity < service["min_amount"]:

        send_message(
            chat_id,
            f"❌ الحد الأدنى هو {service['min_amount']}."
        )

        return True

    if quantity > service["max_amount"]:

        send_message(
            chat_id,
            f"❌ الحد الأقصى هو {service['max_amount']}."
        )

        return True

    total = (
        quantity / 1000
    ) * service["price"]

    user = get_user(
        user_id
    )

    balance = (
        float(user["balance"])
        if user
        else 0
    )

    if balance < total:

        send_message(
            chat_id,
            f"""
❌ الرصيد غير كافٍ.

💳 رصيدك:
{balance:.2f} نقطة

💰 المطلوب:
{total:.2f} نقطة

اشحن رصيدك أولاً.
""".strip()
        )

        PENDING.pop(
            user_id,
            None
        )

        return True

    # خصم الرصيد
    change_balance(
        user_id,
        -total
    )

    connection = db()

    cur = connection.cursor()

    cur.execute("""
        INSERT INTO orders
        (
            user_id,
            service_id,
            target,
            quantity,
            total
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        service_id,
        state["target"],
        quantity,
        total
    ))

    order_id = cur.lastrowid

    connection.commit()
    connection.close()

    PENDING.pop(
        user_id,
        None
    )

    send_message(
        chat_id,
        f"""
✅ تم إنشاء الطلب

🆔 رقم الطلب:
#{order_id}

🛍 الخدمة:
{service['name']}

🎯 الهدف:
{state['target']}

📊 الكمية:
{quantity}

💰 التكلفة:
{total:.2f} نقطة

⏳ الحالة:
بانتظار مراجعة الإدارة.
""".strip()
    )

    # إرسال الطلب للإدارة
    if ADMIN_ID:

        admin_keyboard_buttons = {
            "inline_keyboard": [

                [
                    {
                        "text": "✅ قبول",
                        "callback_data":
                        f"accept:{order_id}"
                    },
                    {
                        "text": "❌ رفض",
                        "callback_data":
                        f"reject:{order_id}"
                    }
                ]
            ]
        }

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
{total:.2f} نقطة

⏳ بانتظار المراجعة.
""".strip(),
            admin_keyboard_buttons
        )

    return True


# =========================================================
# ACCOUNT
# =========================================================

def show_account(
    chat_id,
    user_id
):

    user = get_user(
        user_id
    )

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
{user['balance']:.2f} نقطة
""".strip()

    keyboard = {
        "inline_keyboard": [

            [
                {
                    "text": "💳 شحن الرصيد",
                    "callback_data": "topup"
                }
            ],

            [
                {
                    "text": "🔙 الرئيسية",
                    "callback_data": "home"
                }
            ]
        ]
    }

    send_message(
        chat_id,
        text,
        keyboard
    )


# =========================================================
# ORDERS
# =========================================================

def show_orders(
    chat_id,
    user_id
):

    connection = db()

    rows = connection.execute("""
        SELECT
            orders.*,
            services.name
        FROM orders
        LEFT JOIN services
        ON services.id=orders.service_id
        WHERE orders.user_id=?
        ORDER BY orders.id DESC
        LIMIT 10
    """, (
        user_id,
    )).fetchall()

    connection.close()

    if not rows:

        send_message(
            chat_id,
            "🗓 لا توجد لديك طلبات حتى الآن."
        )

        return

    status_names = {
        "pending": "⏳ بانتظار المراجعة",
        "accepted": "🟢 مقبول",
        "working": "🛠 قيد التنفيذ",
        "completed": "✅ مكتمل",
        "rejected": "❌ مرفوض"
    }

    text = "🗓 آخر الطلبات\n\n"

    for row in rows:

        status = status_names.get(
            row["status"],
            row["status"]
        )

        text += f"""
🆔 #{row['id']}
🛍 {row['name']}
📊 الكمية: {row['quantity']}
💰 {row['total']:.2f} نقطة
{status}

────────────
"""

    send_message(
        chat_id,
        text.strip()
    )


# =========================================================
# TOP UP - TELEGRAM STARS
# =========================================================

def create_invoice(
    chat_id
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

    if not result.get("ok"):

        send_message(
            chat_id,
            "❌ تعذر إنشاء فاتورة الشحن حالياً."
        )


# =========================================================
# STATS
# =========================================================

def show_stats(chat_id):

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

    connection.close()

    send_message(
        chat_id,
        f"""
📉 إحصائيات البوت

👥 المستخدمون:
{users}

🗓 جميع الطلبات:
{orders}

🏅 الطلبات المكتملة:
{completed}
""".strip()
    )


# =========================================================
# ADMIN MENU
# =========================================================

def admin_menu(chat_id):

    if chat_id != ADMIN_ID:
        return

    send_message(
        chat_id,
        f"""
👑 لوحة الإدارة

أهلاً بك في {STORE_NAME}

اختر العملية:
""".strip(),
        admin_keyboard()
    )


# =========================================================
# ADMIN SECTIONS
# =========================================================

def admin_sections(chat_id):

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
            {
                "text":
                f"{status} {row['emoji']} {row['name']}",
                "callback_data":
                f"admin_section:{row['id']}"
            }
        ])

    buttons.append([
        {
            "text": "➕ إضافة قسم",
            "callback_data": "add_section"
        }
    ])

    buttons.append([
        {
            "text": "🔙 الإدارة",
            "callback_data": "admin"
        }
    ])

    send_message(
        chat_id,
        "🛍 إدارة الأقسام",
        {
            "inline_keyboard": buttons
        }
    )


# =========================================================
# ADMIN SERVICES
# =========================================================

def admin_services(chat_id):

    connection = db()

    rows = connection.execute("""
        SELECT
            services.*,
            sections.name AS section_name
        FROM services
        LEFT JOIN sections
        ON sections.id=services.section_id
        ORDER BY services.id DESC
        LIMIT 50
    """).fetchall()

    connection.close()

    buttons = []

    for row in rows:

        status = (
            "🟢"
            if row["enabled"]
            else "🔴"
        )

        buttons.append([
            {
                "text":
                f"{status} {row['name']}",

                "callback_data":
                f"admin_service:{row['id']}"
            }
        ])

    buttons.append([
        {
            "text": "➕ إضافة خدمة",
            "callback_data": "add_service"
        }
    ])

    buttons.append([
        {
            "text": "🔙 الإدارة",
            "callback_data": "admin"
        }
    ])

    send_message(
        chat_id,
        "📉 إدارة الخدمات",
        {
            "inline_keyboard": buttons
        }
    )


# =========================================================
# ADMIN ORDERS
# =========================================================

def admin_orders(chat_id):

    connection = db()

    rows = connection.execute("""
        SELECT
            orders.*,
            services.name
        FROM orders
        LEFT JOIN services
        ON services.id=orders.service_id
        WHERE orders.status='pending'
        ORDER BY orders.id DESC
        LIMIT 20
    """).fetchall()

    connection.close()

    if not rows:

        send_message(
            chat_id,
            "✅ لا توجد طلبات معلقة."
        )

        return

    for row in rows:

        keyboard = {
            "inline_keyboard": [

                [
                    {
                        "text": "✅ قبول",
                        "callback_data":
                        f"accept:{row['id']}"
                    },
                    {
                        "text": "❌ رفض",
                        "callback_data":
                        f"reject:{row['id']}"
                    }
                ]
            ]
        }

        send_message(
            chat_id,
            f"""
🚨 طلب #{row['id']}

🛍 {row['name']}

🎯 {row['target']}

📊 {row['quantity']}

💰 {row['total']:.2f} نقطة

⏳ بانتظار المراجعة.
""".strip(),
            keyboard
        )


# =========================================================
# ACCEPT ORDER
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

    if row["status"] != "pending":
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
        f"""
✅ تم قبول طلبك #{order_id}

🛠 سيتم البدء بتنفيذ الطلب.
""".strip()
    )


# =========================================================
# REJECT ORDER
# =========================================================

def reject_order(order_id):

    connection = db()

    row = connection.execute(
        "SELECT * FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()

    if not row:
        connection.close()
        return

    if row["status"] != "pending":
        connection.close()
        return

    # إرجاع الرصيد
    connection.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE id=?
        """,
        (
            row["total"],
            row["user_id"]
        )
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
{row['total']:.2f} نقطة

إلى رصيدك.
""".strip()
    )


# =========================================================
# CALLBACKS
# =========================================================

def handle_callback(callback):

    callback_id = callback.get("id")
    data = callback.get("data", "")

    message = callback.get(
        "message",
        {}
    )

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get("id")

    user = callback.get(
        "from",
        {}
    )

    user_id = user.get("id")

    if callback_id:
        answer_callback(
            callback_id
        )

    if not chat_id:
        return

    # -------------------------
    # USER
    # -------------------------

    if data == "home":

        start_user(
            chat_id,
            user
        )

        return

    if data == "sections":

        show_sections(
            chat_id
        )

        return

    if data == "account":

        show_account(
            chat_id,
            user_id
        )

        return

    if data == "orders":

        show_orders(
            chat_id,
            user_id
        )

        return

    if data == "stats":

        show_stats(
            chat_id
        )

        return

    if data == "support":

        send_message(
            chat_id,
            "🛡 للدعم تواصل مع الإدارة."
        )

        return

    if data == "topup":

        create_invoice(
            chat_id
        )

        return

    if data.startswith("section:"):

        try:
            section_id = int(
                data.split(":")[1]
            )

            show_services(
                chat_id,
                section_id
            )

        except:
            pass

        return

    if data.startswith("service:"):

        try:
            service_id = int(
                data.split(":")[1]
            )

            show_service(
                chat_id,
                service_id
            )

        except:
            pass

        return

    if data.startswith("order:"):

        try:
            service_id = int(
                data.split(":")[1]
            )

            begin_order(
                user_id,
                chat_id,
                service_id
            )

        except:
            pass

        return

    # -------------------------
    # ADMIN
    # -------------------------

    if user_id != ADMIN_ID:
        return

    if data == "admin":

        admin_menu(
            chat_id
        )

        return

    if data == "admin_sections":

        admin_sections(
            chat_id
        )

        return

    if data == "admin_services":

        admin_services(
            chat_id
        )

        return

    if data == "admin_orders":

        admin_orders(
            chat_id
        )

        return

    if data == "admin_stats":

        show_stats(
            chat_id
        )

        return

    if data.startswith("accept:"):

        try:
            order_id = int(
                data.split(":")[1]
            )

            accept_order(
                order_id
            )

            send_message(
                chat_id,
                f"✅ تم قبول الطلب #{order_id}"
            )

        except:
            pass

        return

    if data.startswith("reject:"):

        try:
            order_id = int(
                data.split(":")[1]
            )

            reject_order(
                order_id
            )

            send_message(
                chat_id,
                f"❌ تم رفض الطلب #{order_id}"
            )

        except:
            pass

        return


# =========================================================
# PAYMENT EVENTS
# =========================================================

def handle_pre_checkout(update):

    query = update.get(
        "pre_checkout_query"
    )

    if not query:
        return

    telegram(
        "answerPreCheckoutQuery",
        {
            "pre_checkout_query_id":
            query["id"],

            "ok": "true"
        }
    )


def handle_successful_payment(
    message
):

    payment = message.get(
        "successful_payment"
    )

    if not payment:
        return

    user = message.get(
        "from",
        {}
    )

    user_id = user.get(
        "id"
    )

    stars = int(
        payment.get(
            "total_amount",
            0
        )
    )

    charge_id = payment.get(
        "telegram_payment_charge_id",
        ""
    )

    if not user_id or stars <= 0:
        return

    # تسجيل العملية
    connection = db()

    connection.execute("""
        INSERT INTO topups
        (
            user_id,
            stars,
            status,
            telegram_charge_id
        )
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        stars,
        "completed",
        charge_id
    ))

    connection.commit()
    connection.close()

    # كل نجمة = نقطة
    change_balance(
        user_id,
        stars
    )

    current = get_user(
        user_id
    )

    balance = (
        current["balance"]
        if current
        else stars
    )

    send_message(
        user_id,
        f"""
✅ تم تأكيد الشحن

⭐ النجوم:
{stars}

💳 تمت إضافة:
{stars} نقطة

💰 رصيدك الحالي:
{balance:.2f} نقطة
""".strip()
    )


# =========================================================
# UPDATE HANDLER
# =========================================================

def handle_update(update):

    # الدفع قبل التأكيد
    if "pre_checkout_query" in update:

        handle_pre_checkout(
            update
        )

        return

    message = update.get(
        "message"
    )

    if message:

        # الدفع الناجح
        if "successful_payment" in message:

            handle_successful_payment(
                message
            )

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

        save_user(
            user
        )

        text = (
            message.get(
                "text",
                ""
            )
            or ""
        ).strip()

        # ADMIN
        if (
            text == "/admin"
            and user_id == ADMIN_ID
        ):

            admin_menu(
                chat_id
            )

            return

        # START
        if text.startswith(
            "/start"
        ):

            start_user(
                chat_id,
                user
            )

            return

        # الطلبات متعددة الخطوات
        if user_id in PENDING:

            state = PENDING[user_id]

            if state["type"] == "order_target":

                receive_order_target(
                    user_id,
                    chat_id,
                    text
                )

                return

            if state["type"] == "order_quantity":

                receive_order_quantity(
                    user_id,
                    chat_id,
                    text
                )

                return

        # HELP
        if text == "/help":

            send_message(
                chat_id,
                """
🛡 المساعدة

🛍 اختر الخدمة
📊 حدد الكمية
💳 تأكد من وجود الرصيد
🗓 تابع حالة طلبك

للدعم تواصل مع الإدارة.
""".strip()
            )

            return

    # CALLBACK
    callback = update.get(
        "callback_query"
    )

    if callback:

        handle_callback(
            callback
        )

        return


# =========================================================
# VERCEL API
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
    "/api",
    methods=["GET"]
)
def api_root():

    return jsonify({
        "ok": True,
        "service": STORE_NAME,
        "status": "online",
        "telegram": "webhook"
    })


@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({
        "ok": True,
        "status": "online"
    })


@app.route(
    "/",
    methods=["POST"]
)
@app.route(
    "/api",
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

        print(
            "TELEGRAM UPDATE:",
            json.dumps(
                update,
                ensure_ascii=False
            )
        )

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

        # نرجع 200 حتى لا يعيد Telegram
        # إرسال نفس التحديث باستمرار

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 200


# =========================================================
# LOCAL
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8000
    )

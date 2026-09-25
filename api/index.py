import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")

WEB_APP_URL = "https://v-alyo.vercel.app/"
TARGET_USERNAME = "@OM_G9"

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# =========================================================
# TEMPORARY DATA
# =========================================================
# ملاحظة:
# هذه البيانات مؤقتة داخل تشغيل الـ Function.
# إذا أردت رصيد وطلبات دائمة حتى بعد إعادة تشغيل Vercel
# نربطها لاحقاً بقاعدة بيانات/Redis بدون تغيير نظام البوت.


users = {}

orders = {}

services = {
    "1": {
        "id": "1",
        "category": "متابعين",
        "name": "متابعين",
        "price": 100,
        "description": "خدمة متابعين"
    },
    "2": {
        "id": "2",
        "category": "مشاهدات",
        "name": "مشاهدات",
        "price": 50,
        "description": "خدمة مشاهدات"
    },
    "3": {
        "id": "3",
        "category": "تفاعلات",
        "name": "تفاعلات",
        "price": 75,
        "description": "خدمة تفاعلات"
    },
    "4": {
        "id": "4",
        "category": "إعجابات",
        "name": "إعجابات",
        "price": 60,
        "description": "خدمة إعجابات"
    }
}

categories = {
    "متابعين",
    "مشاهدات",
    "تفاعلات",
    "إعجابات"
}

pending_admin_actions = {}


# =========================================================
# TELEGRAM API
# =========================================================

def telegram(method, data=None):

    if not BOT_TOKEN:
        return {
            "ok": False,
            "error": "BOT_TOKEN is missing"
        }

    if data is None:
        data = {}

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
            timeout=15
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except Exception as e:

        return {
            "ok": False,
            "error": str(e)
        }


# =========================================================
# TELEGRAM HELPERS
# =========================================================

def send_message(
    chat_id,
    text,
    keyboard=None
):

    data = {
        "chat_id": chat_id,
        "text": text
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


def edit_message(
    chat_id,
    message_id,
    text,
    keyboard=None
):

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }

    if keyboard:

        data["reply_markup"] = json.dumps(
            keyboard,
            ensure_ascii=False
        )

    return telegram(
        "editMessageText",
        data
    )


def answer_callback(callback_id):

    return telegram(
        "answerCallbackQuery",
        {
            "callback_query_id":
            callback_id
        }
    )


def delete_message(
    chat_id,
    message_id
):

    return telegram(
        "deleteMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id
        }
    )


# =========================================================
# USER
# =========================================================

def get_user(user):

    user_id = str(
        user.get("id")
    )

    if user_id not in users:

        users[user_id] = {
            "id": user_id,
            "username":
                user.get("username", ""),
            "first_name":
                user.get("first_name", ""),
            "balance": 0,
            "orders": []
        }

    else:

        users[user_id]["username"] = \
            user.get(
                "username",
                users[user_id].get(
                    "username",
                    ""
                )
            )

    return users[user_id]


def is_admin(user_id):

    return (
        ADMIN_ID
        and str(user_id) == str(ADMIN_ID)
    )


# =========================================================
# MAIN MENU
# =========================================================

def main_menu(user_id):

    keyboard = [
        [
            {
                "text": "🛍️ الخدمات",
                "callback_data": "services"
            },
            {
                "text": "👑 حسابي",
                "callback_data": "account"
            }
        ],
        [
            {
                "text": "💳 شحن الرصيد",
                "callback_data": "recharge"
            },
            {
                "text": "📋 طلباتي",
                "callback_data": "orders"
            }
        ],
        [
            {
                "text": "🔎 فحص الطلب",
                "callback_data": "check_order"
            },
            {
                "text": "📢 تمويل قناتك",
                "callback_data": "promotion"
            }
        ],
        [
            {
                "text": "💎 النقاط",
                "callback_data": "points"
            },
            {
                "text": "🎁 النجوم والجوائز",
                "callback_data": "stars"
            }
        ],
        [
            {
                "text": "🔑 استخدام كود",
                "callback_data": "code"
            },
            {
                "text": "📡 API + التحديثات",
                "callback_data": "api"
            }
        ],
        [
            {
                "text": "🛡️ الدعم",
                "callback_data": "support"
            },
            {
                "text": "⚠️ شروط الاستخدام",
                "callback_data": "terms"
            }
        ]
    ]

    if is_admin(user_id):

        keyboard.append([
            {
                "text": "⚙️ لوحة التحكم",
                "callback_data": "admin"
            }
        ])

    return {
        "inline_keyboard": keyboard
    }


# =========================================================
# START
# =========================================================

def start_user(chat_id, user):

    account = get_user(user)

    username = (
        f"@{account['username']}"
        if account.get("username")
        else account.get(
            "first_name",
            "مستخدم"
        )
    )

    text = (
        "👑 أهلاً بك في بوت الرشق\n\n"
        "🛍️ منصة الخدمات الرقمية\n"
        "⚡ اختر القسم المطلوب من القائمة بالأسفل.\n\n"
        f"👤 الحساب: {username}\n"
        f"💰 رصيدك: {account['balance']} نقطة\n\n"
        "اختر العملية المطلوبة:"
    )

    send_message(
        chat_id,
        text,
        main_menu(
            account["id"]
        )
    )


# =========================================================
# SERVICES
# =========================================================

def services_menu():

    rows = []

    for category in sorted(categories):

        rows.append([
            {
                "text": f"📦 {category}",
                "callback_data":
                    "cat:" + category
            }
        ])

    rows.append([
        {
            "text": "🔙 الرئيسية",
            "callback_data": "home"
        }
    ])

    return {
        "inline_keyboard": rows
    }


def category_menu(category):

    rows = []

    for service in services.values():

        if service["category"] != category:
            continue

        rows.append([
            {
                "text":
                    f"🛒 {service['name']} — {service['price']} نقطة",
                "callback_data":
                    "service:" + service["id"]
            }
        ])

    rows.append([
        {
            "text": "🔙 الخدمات",
            "callback_data": "services"
        }
    ])

    return {
        "inline_keyboard": rows
    }


def service_details(service_id):

    service = services.get(
        service_id
    )

    if not service:
        return (
            "❌ الخدمة غير موجودة.",
            services_menu()
        )

    text = (
        "🛍️ تفاصيل الخدمة\n\n"
        f"📦 الخدمة: {service['name']}\n"
        f"📂 القسم: {service['category']}\n"
        f"💰 السعر: {service['price']} نقطة\n\n"
        f"📝 {service['description']}\n\n"
        "اضغط طلب الخدمة للمتابعة."
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🛒 طلب الخدمة",
                    "callback_data":
                        "order:" + service_id
                }
            ],
            [
                {
                    "text": "🔙 رجوع",
                    "callback_data":
                        "cat:" +
                        service["category"]
                }
            ]
        ]
    }

    return text, keyboard


# =========================================================
# ORDER
# =========================================================

def create_order(user, service_id):

    service = services.get(
        service_id
    )

    if not service:
        return None

    user_id = str(
        user["id"]
    )

    account = get_user(user)

    order_id = str(
        len(orders) + 1
    )

    order = {
        "id": order_id,
        "user_id": user_id,
        "username":
            account.get(
                "username",
                ""
            ),
        "service_id": service_id,
        "service":
            service["name"],
        "category":
            service["category"],
        "price":
            service["price"],
        "status":
            "pending",
        "created":
            datetime.utcnow().isoformat()
    }

    orders[order_id] = order

    account["orders"].append(
        order_id
    )

    return order


def notify_admin(order):

    if not ADMIN_ID:
        return

    username = (
        "@" + order["username"]
        if order.get("username")
        else "بدون معرف"
    )

    text = (
        "🆕 طلب جديد\n\n"
        f"🆔 رقم الطلب: #{order['id']}\n"
        f"👤 المستخدم: {username}\n"
        f"🔢 ID: {order['user_id']}\n"
        f"🛍️ الخدمة: {order['service']}\n"
        f"📂 القسم: {order['category']}\n"
        f"💰 السعر: {order['price']} نقطة\n\n"
        "⏳ الطلب بانتظار موافقتك."
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🟢 موافقة",
                    "callback_data":
                        "approve:" +
                        order["id"]
                },
                {
                    "text": "🔴 رفض",
                    "callback_data":
                        "reject:" +
                        order["id"]
                }
            ]
        ]
    }

    send_message(
        ADMIN_ID,
        text,
        keyboard
    )


# =========================================================
# ACCOUNT
# =========================================================

def account_page(user):

    account = get_user(user)

    username = (
        "@" + account["username"]
        if account.get("username")
        else "بدون معرف"
    )

    text = (
        "👑 حسابي\n\n"
        f"👤 المستخدم: {username}\n"
        f"🆔 ID: {account['id']}\n"
        f"💰 الرصيد: {account['balance']} نقطة\n"
        f"📋 عدد الطلبات: "
        f"{len(account['orders'])}\n"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "💳 شحن الرصيد",
                    "callback_data": "recharge"
                }
            ],
            [
                {
                    "text": "📋 طلباتي",
                    "callback_data": "orders"
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

    return text, keyboard


# =========================================================
# ORDERS
# =========================================================

def orders_page(user):

    account = get_user(user)

    if not account["orders"]:

        text = (
            "📋 طلباتي\n\n"
            "لا توجد لديك طلبات حالياً."
        )

    else:

        lines = [
            "📋 آخر الطلبات:",
            ""
        ]

        for order_id in reversed(
            account["orders"][-10:]
        ):

            order = orders.get(
                order_id
            )

            if not order:
                continue

            status = {
                "pending":
                    "⏳ بانتظار الموافقة",
                "approved":
                    "🟢 تمت الموافقة",
                "running":
                    "▶️ قيد التنفيذ",
                "completed":
                    "✅ مكتمل",
                "rejected":
                    "🔴 مرفوض"
            }.get(
                order["status"],
                order["status"]
            )

            lines.append(
                f"#{order['id']} — "
                f"{order['service']}\n"
                f"{status}"
            )

        text = "\n\n".join(
            lines
        )

    return (
        text,
        {
            "inline_keyboard": [
                [
                    {
                        "text": "🔙 الرئيسية",
                        "callback_data":
                            "home"
                    }
                ]
            ]
        }
    )


# =========================================================
# ADMIN PANEL
# =========================================================

def admin_menu():

    return {
        "inline_keyboard": [
            [
                {
                    "text": "📦 إدارة الخدمات",
                    "callback_data":
                        "admin_services"
                }
            ],
            [
                {
                    "text": "📂 إضافة قسم",
                    "callback_data":
                        "admin_add_category"
                },
                {
                    "text": "➕ إضافة خدمة",
                    "callback_data":
                        "admin_add_service"
                }
            ],
            [
                {
                    "text": "📋 الطلبات المعلقة",
                    "callback_data":
                        "admin_pending"
                }
            ],
            [
                {
                    "text": "📊 الإحصائيات",
                    "callback_data":
                        "admin_stats"
                }
            ],
            [
                {
                    "text": "🔙 الرئيسية",
                    "callback_data":
                        "home"
                }
            ]
        ]
    }


def admin_services_page():

    rows = []

    for service in services.values():

        rows.append([
            {
                "text":
                    f"📦 {service['name']} "
                    f"({service['price']})",
                "callback_data":
                    "admin_service:" +
                    service["id"]
            }
        ])

    rows.append([
        {
            "text": "➕ إضافة خدمة",
            "callback_data":
                "admin_add_service"
        }
    ])

    rows.append([
        {
            "text": "🔙 لوحة التحكم",
            "callback_data":
                "admin"
        }
    ])

    return {
        "inline_keyboard":
            rows
    }


def pending_orders_page():

    rows = []

    for order in orders.values():

        if order["status"] != "pending":
            continue

        rows.append([
            {
                "text":
                    f"🆕 #{order['id']} "
                    f"{order['service']}",
                "callback_data":
                    "admin_order:" +
                    order["id"]
            }
        ])

    if not rows:

        return {
            "inline_keyboard": [
                [
                    {
                        "text":
                            "🔙 لوحة التحكم",
                        "callback_data":
                            "admin"
                    }
                ]
            ]
        }

    rows.append([
        {
            "text":
                "🔙 لوحة التحكم",
            "callback_data":
                "admin"
        }
    ])

    return {
        "inline_keyboard":
            rows
    }


def admin_order_page(order_id):

    order = orders.get(
        order_id
    )

    if not order:

        return (
            "❌ الطلب غير موجود.",
            pending_orders_page()
        )

    username = (
        "@" + order["username"]
        if order.get("username")
        else "بدون معرف"
    )

    text = (
        "📋 تفاصيل الطلب\n\n"
        f"🆔 #{order['id']}\n"
        f"👤 {username}\n"
        f"🔢 ID: {order['user_id']}\n"
        f"🛍️ {order['service']}\n"
        f"📂 {order['category']}\n"
        f"💰 {order['price']} نقطة\n"
        f"📌 الحالة: {order['status']}"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🟢 موافقة",
                    "callback_data":
                        "approve:" +
                        order_id
                },
                {
                    "text": "🔴 رفض",
                    "callback_data":
                        "reject:" +
                        order_id
                }
            ],
            [
                {
                    "text": "🔙 الطلبات",
                    "callback_data":
                        "admin_pending"
                }
            ]
        ]
    }

    return text, keyboard


# =========================================================
# ADMIN ACTIONS
# =========================================================

def approve_order(order_id):

    order = orders.get(
        order_id
    )

    if not order:
        return

    if order["status"] != "pending":
        return

    order["status"] = "approved"

    send_message(
        order["user_id"],
        (
            "🟢 تمت الموافقة على طلبك\n\n"
            f"🆔 رقم الطلب: #{order['id']}\n"
            f"🛍️ الخدمة: {order['service']}\n\n"
            "⏳ الطلب الآن جاهز للتشغيل."
        ),
        {
            "inline_keyboard": [
                [
                    {
                        "text": "📋 طلباتي",
                        "callback_data":
                            "orders"
                    }
                ]
            ]
        }
    )


def reject_order(order_id):

    order = orders.get(
        order_id
    )

    if not order:
        return

    if order["status"] in [
        "completed",
        "rejected"
    ]:
        return

    order["status"] = "rejected"

    send_message(
        order["user_id"],
        (
            "🔴 تم رفض طلبك\n\n"
            f"🆔 رقم الطلب: #{order['id']}\n"
            f"🛍️ الخدمة: {order['service']}"
        )
    )


def run_order(order_id):

    order = orders.get(
        order_id
    )

    if not order:
        return

    if order["status"] != "approved":
        return

    order["status"] = "running"

    send_message(
        order["user_id"],
        (
            "▶️ تم تشغيل طلبك\n\n"
            f"🆔 #{order['id']}\n"
            f"🛍️ {order['service']}\n\n"
            "⏳ الطلب قيد التنفيذ."
        )
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

def handle_callback(callback):

    callback_id = callback.get(
        "id"
    )

    data = callback.get(
        "data",
        ""
    )

    message = callback.get(
        "message"
    )

    if not message:
        return

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get(
        "id"
    )

    message_id = message.get(
        "message_id"
    )

    user = callback.get(
        "from",
        {}
    )

    user_id = str(
        user.get("id")
    )

    account = get_user(
        user
    )

    answer_callback(
        callback_id
    )

    # -----------------------------------------------------
    # HOME
    # -----------------------------------------------------

    if data == "home":

        text = (
            "👑 أهلاً بك في بوت الرشق\n\n"
            "🛍️ منصة الخدمات الرقمية\n"
            "⚡ اختر القسم المطلوب:"
        )

        edit_message(
            chat_id,
            message_id,
            text,
            main_menu(user_id)
        )

        return

    # -----------------------------------------------------
    # SERVICES
    # -----------------------------------------------------

    if data == "services":

        edit_message(
            chat_id,
            message_id,
            "🛍️ اختر القسم المطلوب:",
            services_menu()
        )

        return

    if data.startswith("cat:"):

        category = data.split(
            ":",
            1
        )[1]

        edit_message(
            chat_id,
            message_id,
            f"📦 خدمات قسم {category}:",
            category_menu(category)
        )

        return

    if data.startswith("service:"):

        service_id = data.split(
            ":",
            1
        )[1]

        text, keyboard = \
            service_details(
                service_id
            )

        edit_message(
            chat_id,
            message_id,
            text,
            keyboard
        )

        return

    # -----------------------------------------------------
    # CREATE ORDER
    # -----------------------------------------------------

    if data.startswith("order:"):

        service_id = data.split(
            ":",
            1
        )[1]

        service = services.get(
            service_id
        )

        if not service:
            return

        if account["balance"] < \
                service["price"]:

            edit_message(
                chat_id,
                message_id,
                (
                    "❌ رصيدك غير كافٍ.\n\n"
                    f"💰 رصيدك: "
                    f"{account['balance']}\n"
                    f"💳 المطلوب: "
                    f"{service['price']}"
                ),
                {
                    "inline_keyboard": [
                        [
                            {
                                "text":
                                    "💳 شحن الرصيد",
                                "callback_data":
                                    "recharge"
                            }
                        ],
                        [
                            {
                                "text":
                                    "🔙 رجوع",
                                "callback_data":
                                    "cat:" +
                                    service[
                                        "category"
                                    ]
                            }
                        ]
                    ]
                }
            )

            return

        order = create_order(
            user,
            service_id
        )

        if not order:
            return

        # خصم الرصيد عند إنشاء الطلب
        account["balance"] -= \
            service["price"]

        notify_admin(
            order
        )

        edit_message(
            chat_id,
            message_id,
            (
                "✅ تم إرسال طلبك بنجاح\n\n"
                f"🆔 رقم الطلب: #{order['id']}\n"
                f"🛍️ الخدمة: {order['service']}\n"
                f"💰 التكلفة: "
                f"{order['price']} نقطة\n\n"
                "⏳ طلبك الآن بانتظار "
                "موافقة الإدارة."
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "📋 طلباتي",
                            "callback_data":
                                "orders"
                        }
                    ],
                    [
                        {
                            "text":
                                "🔙 الرئيسية",
                            "callback_data":
                                "home"
                        }
                    ]
                ]
            }
        )

        return

    # -----------------------------------------------------
    # ACCOUNT
    # -----------------------------------------------------

    if data == "account":

        text, keyboard = \
            account_page(
                user
            )

        edit_message(
            chat_id,
            message_id,
            text,
            keyboard
        )

        return

    # -----------------------------------------------------
    # ORDERS
    # -----------------------------------------------------

    if data == "orders":

        text, keyboard = \
            orders_page(
                user
            )

        edit_message(
            chat_id,
            message_id,
            text,
            keyboard
        )

        return

    # -----------------------------------------------------
    # RECHARGE
    # -----------------------------------------------------

    if data == "recharge":

        edit_message(
            chat_id,
            message_id,
            (
                "💳 شحن الرصيد\n\n"
                "لشحن رصيدك، تواصل مع الدعم "
                "وأرسل المبلغ المطلوب.\n\n"
                "📌 بعد تأكيد الدفع يتم إضافة "
                "الرصيد من لوحة الإدارة."
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "🛡️ التواصل مع الدعم",
                            "callback_data":
                                "support"
                        }
                    ],
                    [
                        {
                            "text":
                                "🔙 الرئيسية",
                            "callback_data":
                                "home"
                        }
                    ]
                ]
            }
        )

        return

    # -----------------------------------------------------
    # SUPPORT
    # -----------------------------------------------------

    if data == "support":

        edit_message(
            chat_id,
            message_id,
            (
                "🛡️ الدعم\n\n"
                "للمساعدة أو شحن الرصيد "
                "تواصل مع الإدارة."
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "🔙 الرئيسية",
                            "callback_data":
                                "home"
                        }
                    ]
                ]
            }
        )

        return

    # -----------------------------------------------------
    # TERMS
    # -----------------------------------------------------

    if data == "terms":

        edit_message(
            chat_id,
            message_id,
            (
                "⚠️ شروط الاستخدام\n\n"
                "• يمنع استخدام الخدمات في "
                "أي نشاط مخالف للقوانين.\n"
                "• الطلبات تخضع للمراجعة.\n"
                "• بعد الموافقة يبدأ التنفيذ "
                "حسب الخدمة المتاحة.\n"
                "• يرجى التأكد من بيانات الطلب "
                "قبل الإرسال."
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "🔙 الرئيسية",
                            "callback_data":
                                "home"
                        }
                    ]
                ]
            }
        )

        return

    # -----------------------------------------------------
    # OTHER PAGES
    # -----------------------------------------------------

    if data == "promotion":

        edit_message(
            chat_id,
            message_id,
            (
                "📢 تمويل قناتك\n\n"
                "يمكنك طلب خدمة تمويل القناة "
                "من قسم الخدمات."
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "🛍️ الخدمات",
                            "callback_data":
                                "services"
                        }
                    ],
                    [
                        {
                            "text":
                                "🔙 الرئيسية",
                            "callback_data":
                                "home"
                        }
                    ]
                ]
            }
        )

        return

    if data == "points":

        edit_message(
            chat_id,
            message_id,
            (
                "💎 نظام النقاط\n\n"
                "رصيدك الحالي:\n"
                f"💎 {account['balance']} نقطة"
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "💳 شحن الرصيد",
                            "callback_data":
                                "recharge"
                        }
                    ],
                    [
                        {
                            "text":
                                "🔙 الرئيسية",
                            "callback_data":
                                "home"
                        }
                    ]
                ]
            }
        )

        return

    if data == "stars":

        edit_message(
            chat_id,
            message_id,
            (
                "🎁 النجوم والجوائز\n\n"
                "قسم النجوم والجوائز يمكن "
                "ربطه لاحقاً بنظامك الخاص."
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "🔙 الرئيسية",
                            "callback_data":
                                "home"
                        }
                    ]
                ]
            }
        )

        return

    if data == "code":

        edit_message(
            chat_id,
            message_id,
            (
                "🔑 استخدام كود\n\n"
                "أرسل الكود للدعم حتى يتم "
                "التحقق منه وتفعيله."
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "🔙 الرئيسية",
                            "callback_data":
                                "home"
                        }
                    ]
                ]
            }
        )

        return

    if data == "api":

        edit_message(
            chat_id,
            message_id,
            (
                "📡 API + التحديثات\n\n"
                "يمكن إضافة API للخدمات "
                "لاحقاً وربطه بمزود الخدمة."
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "🔙 الرئيسية",
                            "callback_data":
                                "home"
                        }
                    ]
                ]
            }
        )

        return

    if data == "check_order":

        edit_message(
            chat_id,
            message_id,
            (
                "🔎 فحص الطلب\n\n"
                "افتح قسم طلباتي حتى تشاهد "
                "حالة طلباتك الحالية."
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "📋 طلباتي",
                            "callback_data":
                                "orders"
                        }
                    ],
                    [
                        {
                            "text":
                                "🔙 الرئيسية",
                            "callback_data":
                                "home"
                        }
                    ]
                ]
            }
        )

        return

    # =====================================================
    # ADMIN
    # =====================================================

    if data == "admin":

        if not is_admin(user_id):
            return

        edit_message(
            chat_id,
            message_id,
            (
                "⚙️ لوحة تحكم الإدارة\n\n"
                "اختر العملية:"
            ),
            admin_menu()
        )

        return

    if data == "admin_services":

        if not is_admin(user_id):
            return

        edit_message(
            chat_id,
            message_id,
            "📦 إدارة الخدمات:",
            admin_services_page()
        )

        return

    if data == "admin_pending":

        if not is_admin(user_id):
            return

        edit_message(
            chat_id,
            message_id,
            "📋 الطلبات المعلقة:",
            pending_orders_page()
        )

        return

    if data == "admin_stats":

        if not is_admin(user_id):
            return

        total = len(orders)

        pending = len([
            x for x in orders.values()
            if x["status"] == "pending"
        ])

        approved = len([
            x for x in orders.values()
            if x["status"] == "approved"
        ])

        running = len([
            x for x in orders.values()
            if x["status"] == "running"
        ])

        text = (
            "📊 الإحصائيات\n\n"
            f"👥 المستخدمون: {len(users)}\n"
            f"📋 جميع الطلبات: {total}\n"
            f"⏳ معلقة: {pending}\n"
            f"🟢 موافق عليها: {approved}\n"
            f"▶️ قيد التنفيذ: {running}\n"
            f"📦 الخدمات: {len(services)}"
        )

        edit_message(
            chat_id,
            message_id,
            text,
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "🔙 لوحة التحكم",
                            "callback_data":
                                "admin"
                        }
                    ]
                ]
            }
        )

        return

    # -----------------------------------------------------
    # ADMIN ORDER
    # -----------------------------------------------------

    if data.startswith("admin_order:"):

        if not is_admin(user_id):
            return

        order_id = data.split(
            ":",
            1
        )[1]

        text, keyboard = \
            admin_order_page(
                order_id
            )

        edit_message(
            chat_id,
            message_id,
            text,
            keyboard
        )

        return

    # -----------------------------------------------------
    # APPROVE
    # -----------------------------------------------------

    if data.startswith("approve:"):

        if not is_admin(user_id):
            return

        order_id = data.split(
            ":",
            1
        )[1]

        approve_order(
            order_id
        )

        order = orders.get(
            order_id
        )

        if order:

            edit_message(
                chat_id,
                message_id,
                (
                    "🟢 تمت الموافقة على الطلب\n\n"
                    f"🆔 #{order_id}\n"
                    f"🛍️ {order['service']}\n\n"
                    "الطلب الآن جاهز للتشغيل."
                ),
                {
                    "inline_keyboard": [
                        [
                            {
                                "text":
                                    "▶️ تشغيل الطلب",
                                "callback_data":
                                    "run:" +
                                    order_id
                            }
                        ],
                        [
                            {
                                "text":
                                    "🔙 الطلبات",
                                "callback_data":
                                    "admin_pending"
                            }
                        ]
                    ]
                }
            )

        return

    # -----------------------------------------------------
    # REJECT
    # -----------------------------------------------------

    if data.startswith("reject:"):

        if not is_admin(user_id):
            return

        order_id = data.split(
            ":",
            1
        )[1]

        reject_order(
            order_id
        )

        edit_message(
            chat_id,
            message_id,
            (
                "🔴 تم رفض الطلب\n\n"
                f"🆔 #{order_id}"
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "🔙 الطلبات",
                            "callback_data":
                                "admin_pending"
                        }
                    ]
                ]
            }
        )

        return

    # -----------------------------------------------------
    # RUN
    # -----------------------------------------------------

    if data.startswith("run:"):

        if not is_admin(user_id):
            return

        order_id = data.split(
            ":",
            1
        )[1]

        run_order(
            order_id
        )

        edit_message(
            chat_id,
            message_id,
            (
                "▶️ تم تشغيل الطلب يدويًا\n\n"
                f"🆔 #{order_id}\n\n"
                "الطلب أصبح قيد التنفيذ."
            ),
            {
                "inline_keyboard": [
                    [
                        {
                            "text":
                                "🔙 الطلبات",
                            "callback_data":
                                "admin_pending"
                        }
                    ],
                    [
                        {
                            "text":
                                "⚙️ لوحة التحكم",
                            "callback_data":
                                "admin"
                        }
                    ]
                ]
            }
        )

        return


# =========================================================
# MESSAGE HANDLER
# =========================================================

def handle_message(message):

    chat = message.get(
        "chat"
    )

    if not chat:
        return

    chat_id = chat.get(
        "id"
    )

    user = message.get(
        "from",
        {}
    )

    if not chat_id:
        return

    account = get_user(
        user
    )

    text = message.get(
        "text",
        ""
    )

    # START

    if text.startswith(
        "/start"
    ):

        start_user(
            chat_id,
            user
        )

        return

    # HELP

    if text.startswith(
        "/help"
    ):

        send_message(
            chat_id,
            "🛍️ استخدم القائمة الرئيسية:",
            main_menu(
                account["id"]
            )
        )

        return

    # ADMIN COMMAND

    if text.startswith(
        "/admin"
    ):

        if is_admin(
            account["id"]
        ):

            send_message(
                chat_id,
                "⚙️ لوحة تحكم الإدارة:",
                admin_menu()
            )

        return


# =========================================================
# UPDATE HANDLER
# =========================================================

def handle_update(update):

    if not isinstance(
        update,
        dict
    ):
        return

    # رسالة

    if update.get("message"):

        handle_message(
            update["message"]
        )

        return

    # زر Inline

    if update.get(
        "callback_query"
    ):

        handle_callback(
            update["callback_query"]
        )

        return


# =========================================================
# VERCEL HTTP HANDLER
# =========================================================

class Handler(
    BaseHTTPRequestHandler
):

    def send_json(
        self,
        data,
        status=200
    ):

        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(
            body
        )

    def do_GET(self):

        self.send_json({
            "ok": True,
            "service":
                "Telegram Gift Bot",
            "status":
                "online",
            "telegram":
                "webhook",
            "web_app":
                WEB_APP_URL,
            "users":
                len(users),
            "orders":
                len(orders),
            "services":
                len(services)
        })

    def do_POST(self):

        try:

            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            raw = self.rfile.read(
                length
            )

            if not raw:

                self.send_json({
                    "ok": True
                })

                return

            update = json.loads(
                raw.decode("utf-8")
            )

            handle_update(
                update
            )

            self.send_json({
                "ok": True
            })

        except Exception as e:

            self.send_json(
                {
                    "ok": False,
                    "error":
                        str(e)
                },
                200
            )


handler = Handler

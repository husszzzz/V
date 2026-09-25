import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler


# =========================================================
# Environment Variables
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMIN_ID = os.environ.get("ADMIN_ID", "").strip()
SETUP_KEY = os.environ.get("SETUP_KEY", "").strip()
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").strip().rstrip("/")


# =========================================================
# Telegram API
# =========================================================

def telegram(method, data=None):
    if not BOT_TOKEN:
        return {
            "ok": False,
            "error": "BOT_TOKEN is not configured"
        }

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    payload = json.dumps(
        data or {},
        ensure_ascii=False
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)

    except Exception as error:
        return {
            "ok": False,
            "error": str(error)
        }


# =========================================================
# Send Message
# =========================================================

def send_message(chat_id, text):
    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


# =========================================================
# Send 1 Star Invoice
# =========================================================

def send_star_invoice(chat_id):

    return telegram(
        "sendInvoice",
        {
            "chat_id": chat_id,

            "title": "تجربة دفع نجمة واحدة",

            "description": "تجربة Telegram Stars ⭐ — السعر نجمة واحدة فقط",

            "payload": "TEST_STAR_1",

            # Telegram Stars لا تحتاج provider_token
            "currency": "XTR",

            "prices": [
                {
                    "label": "تجربة",
                    "amount": 1
                }
            ]
        }
    )


# =========================================================
# Handle Telegram Update
# =========================================================

def handle_update(update):

    message = update.get("message")

    # -----------------------------------------------------
    # Messages
    # -----------------------------------------------------

    if message:

        chat = message.get("chat", {})
        chat_id = chat.get("id")

        text = message.get("text", "")

        if not chat_id:
            return

        # -------------------------------------------------
        # /start
        # -------------------------------------------------

        if text.startswith("/start"):

            send_message(
                chat_id,
                "⭐ مرحباً بك في بوت تجربة Telegram Stars\n\n"
                "سيتم إرسال فاتورة بقيمة نجمة واحدة فقط."
            )

            result = send_star_invoice(chat_id)

            # إذا فشل إرسال الفاتورة نبلغ المستخدم
            if not result.get("ok"):

                send_message(
                    chat_id,
                    "❌ حدث خطأ أثناء إنشاء فاتورة الدفع.\n\n"
                    "تحقق من إعدادات البوت في Vercel."
                )

        # -------------------------------------------------
        # /pay
        # -------------------------------------------------

        elif text.startswith("/pay"):

            result = send_star_invoice(chat_id)

            if not result.get("ok"):

                send_message(
                    chat_id,
                    "❌ تعذر إنشاء فاتورة الدفع."
                )

        # -------------------------------------------------
        # Successful Payment
        # -------------------------------------------------

        successful_payment = message.get(
            "successful_payment"
        )

        if successful_payment:

            amount = successful_payment.get(
                "total_amount",
                0
            )

            currency = successful_payment.get(
                "currency",
                ""
            )

            payload = successful_payment.get(
                "invoice_payload",
                ""
            )

            charge_id = successful_payment.get(
                "telegram_payment_charge_id",
                ""
            )

            # لا نعتمد على رسالة النجاح إلا إذا كانت
            # فاتورتنا التجريبية
            if payload == "TEST_STAR_1":

                send_message(
                    chat_id,

                    "✅ تم الدفع بنجاح!\n\n"
                    f"⭐ المبلغ: {amount}\n"
                    f"💳 العملة: {currency}\n\n"
                    "وصلت عملية الدفع إلى البوت."
                )

                # إرسال إشعار للمالك
                if ADMIN_ID:

                    user = message.get(
                        "from",
                        {}
                    )

                    first_name = user.get(
                        "first_name",
                        "غير معروف"
                    )

                    username = user.get(
                        "username"
                    )

                    username_text = (
                        f"@{username}"
                        if username
                        else "بدون معرف"
                    )

                    admin_text = (
                        "💰 عملية Telegram Stars جديدة\n\n"

                        f"👤 الاسم: {first_name}\n"

                        f"🔹 المستخدم: {username_text}\n"

                        f"⭐ المبلغ: {amount} Stars\n"

                        f"💳 العملة: {currency}\n\n"

                        f"🧾 Charge ID:\n"
                        f"{charge_id}"
                    )

                    send_message(
                        ADMIN_ID,
                        admin_text
                    )

    # -----------------------------------------------------
    # Pre Checkout Query
    # -----------------------------------------------------

    pre_checkout = update.get(
        "pre_checkout_query"
    )

    if pre_checkout:

        query_id = pre_checkout.get("id")

        payload = pre_checkout.get(
            "invoice_payload"
        )

        currency = pre_checkout.get(
            "currency"
        )

        amount = pre_checkout.get(
            "total_amount"
        )

        # نتحقق أن الفاتورة هي فاتورتنا
        if (
            payload == "TEST_STAR_1"
            and currency == "XTR"
            and amount == 1
        ):

            telegram(
                "answerPreCheckoutQuery",
                {
                    "pre_checkout_query_id": query_id,
                    "ok": True
                }
            )

        else:

            telegram(
                "answerPreCheckoutQuery",
                {
                    "pre_checkout_query_id": query_id,
                    "ok": False,
                    "error_message": "الفاتورة غير صالحة."
                }
            )


# =========================================================
# HTTP Handler
# =========================================================

class handler(BaseHTTPRequestHandler):

    # -----------------------------------------------------
    # JSON Response
    # -----------------------------------------------------

    def send_json(self, data, status=200):

        output = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.send_header(
            "Content-Length",
            str(len(output))
        )

        self.end_headers()

        self.wfile.write(output)

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    def do_GET(self):

        parsed = urllib.parse.urlparse(
            self.path
        )

        path = parsed.path

        params = urllib.parse.parse_qs(
            parsed.query
        )

        # -------------------------------------------------
        # /api
        # -------------------------------------------------

        if path == "/api":

            action = params.get(
                "action",
                [""]
            )[0]

            # ---------------------------------------------
            # Basic API Test
            # ---------------------------------------------

            if action == "":

                self.send_json(
                    {
                        "ok": True,
                        "service": "Telegram Stars Test Bot",
                        "status": "running"
                    }
                )

                return

            # ---------------------------------------------
            # Setup Webhook
            # ---------------------------------------------

            if action == "setup":

                key = params.get(
                    "key",
                    [""]
                )[0]

                if not SETUP_KEY:

                    self.send_json(
                        {
                            "ok": False,
                            "error": "SETUP_KEY is not configured"
                        },
                        500
                    )

                    return

                if key != SETUP_KEY:

                    self.send_json(
                        {
                            "ok": False,
                            "error": "Invalid setup key"
                        },
                        403
                    )

                    return

                if not WEBHOOK_URL:

                    self.send_json(
                        {
                            "ok": False,
                            "error": "WEBHOOK_URL is not configured"
                        },
                        500
                    )

                    return

                webhook_url = (
                    f"{WEBHOOK_URL}/api"
                )

                result = telegram(
                    "setWebhook",
                    {
                        "url": webhook_url
                    }
                )

                self.send_json(
                    {
                        "webhook_url": webhook_url,
                        "telegram": result
                    }
                )

                return

            # ---------------------------------------------
            # Webhook Status
            # ---------------------------------------------

            if action == "status":

                result = telegram(
                    "getWebhookInfo"
                )

                self.send_json(
                    result
                )

                return

            # ---------------------------------------------
            # Bot Information
            # ---------------------------------------------

            if action == "bot":

                result = telegram(
                    "getMe"
                )

                self.send_json(
                    result
                )

                return

            # ---------------------------------------------
            # Stars Balance
            # ---------------------------------------------

            if action == "balance":

                result = telegram(
                    "getMyStarBalance"
                )

                self.send_json(
                    result
                )

                return

            # ---------------------------------------------
            # Unknown Action
            # ---------------------------------------------

            self.send_json(
                {
                    "ok": False,
                    "error": "Unknown action"
                },
                400
            )

            return

        # -------------------------------------------------
        # Other paths
        # -------------------------------------------------

        self.send_json(
            {
                "ok": False,
                "error": "Not Found"
            },
            404
        )

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    def do_POST(self):

        parsed = urllib.parse.urlparse(
            self.path
        )

        path = parsed.path

        # Telegram Webhook
        if path != "/api":

            self.send_json(
                {
                    "ok": False,
                    "error": "Not Found"
                },
                404
            )

            return

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            body = self.rfile.read(
                content_length
            )

            update = json.loads(
                body.decode("utf-8")
            )

            handle_update(
                update
            )

            # Telegram يحتاج استجابة سريعة
            self.send_json(
                {
                    "ok": True
                }
            )

        except Exception as error:

            self.send_json(
                {
                    "ok": False,
                    "error": str(error)
                },
                500
            )

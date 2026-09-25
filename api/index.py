import os
import json
import urllib.request
import urllib.error

from http.server import BaseHTTPRequestHandler


BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")
SETUP_KEY = os.environ.get("SETUP_KEY", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")


def telegram(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    body = json.dumps(data or {}).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


def send_message(chat_id, text):
    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


def send_star_invoice(chat_id):
    return telegram(
        "sendInvoice",
        {
            "chat_id": chat_id,

            "title": "تجربة دفع نجمة",

            "description": "تجربة Telegram Stars — السعر نجمة واحدة فقط ⭐",

            "payload": "TEST_STAR_1",

            "provider_token": "",

            "currency": "XTR",

            "prices": [
                {
                    "label": "تجربة دفع",
                    "amount": 1
                }
            ]
        }
    )


def handle_update(update):
    # /start
    message = update.get("message")

    if message:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if text.startswith("/start"):
            send_message(
                chat_id,
                "⭐ تجربة Telegram Stars\n\n"
                "اضغط الزر التالي لإظهار فاتورة دفع نجمة واحدة."
            )

            send_star_invoice(chat_id)

    # Pre Checkout
    pre_checkout = update.get("pre_checkout_query")

    if pre_checkout:
        query_id = pre_checkout["id"]

        # نتأكد أن الفاتورة هي فاتورتنا
        if pre_checkout.get("invoice_payload") == "TEST_STAR_1":
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
                    "error_message": "فاتورة غير معروفة."
                }
            )

    # Successful Payment
    if message and message.get("successful_payment"):
        payment = message["successful_payment"]

        amount = payment.get("total_amount")
        currency = payment.get("currency")
        charge_id = payment.get("telegram_payment_charge_id")

        send_message(
            chat_id,
            "✅ تم الدفع بنجاح!\n\n"
            f"⭐ المبلغ: {amount}\n"
            f"💰 العملة: {currency}\n\n"
            "هذه العملية وصلت إلى رصيد Stars الخاص بالبوت."
        )

        # إرسال إشعار للمالك
        if ADMIN_ID:
            username = message.get("from", {}).get("username", "")
            first_name = message.get("from", {}).get("first_name", "")

            send_message(
                ADMIN_ID,
                "💰 عملية Stars جديدة\n\n"
                f"👤 المستخدم: {first_name}\n"
                f"🔹 Username: @{username if username else 'بدون'}\n"
                f"⭐ المبلغ: {amount} Stars\n"
                f"🧾 Charge ID:\n{charge_id}"
            )


class handler(BaseHTTPRequestHandler):

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
            "Content-Length",
            str(len(output))
        )

        self.end_headers()
        self.wfile.write(output)

    def do_GET(self):
        path = self.path.split("?")[0]

        # فحص الموقع
        if path == "/api":
            self.send_json({
                "ok": True,
                "service": "Telegram Stars Test Bot"
            })
            return

        # إعداد Webhook
        if path == "/api/setup":

            if not SETUP_KEY:
                self.send_json({
                    "ok": False,
                    "error": "SETUP_KEY غير موجود"
                }, 500)
                return

            query = self.path.split("?", 1)

            if len(query) < 2:
                self.send_json({
                    "ok": False,
                    "error": "استخدم ?key=..."
                }, 403)
                return

            params = {}

            for item in query[1].split("&"):
                if "=" in item:
                    key, value = item.split("=", 1)
                    params[key] = value

            if params.get("key") != SETUP_KEY:
                self.send_json({
                    "ok": False,
                    "error": "Unauthorized"
                }, 403)
                return

            if not WEBHOOK_URL:
                self.send_json({
                    "ok": False,
                    "error": "WEBHOOK_URL غير موجود"
                }, 500)
                return

            result = telegram(
                "setWebhook",
                {
                    "url": f"{WEBHOOK_URL}/api"
                }
            )

            self.send_json(result)
            return

        # معلومات Webhook
        if path == "/api/status":

            result = telegram("getWebhookInfo")

            self.send_json(result)
            return

        self.send_json({
            "ok": True,
            "message": "Telegram Stars bot is running."
        })

    def do_POST(self):

        path = self.path.split("?")[0]

        if path != "/api":
            self.send_json({
                "ok": False,
                "error": "Not Found"
            }, 404)
            return

        try:
            length = int(
                self.headers.get("Content-Length", "0")
            )

            body = self.rfile.read(length)

            update = json.loads(
                body.decode("utf-8")
            )

            handle_update(update)

            # Telegram يحتاج استجابة سريعة للـWebhook
            self.send_json({
                "ok": True
            })

        except Exception as e:

            self.send_json({
                "ok": False,
                "error": str(e)
            }, 500)

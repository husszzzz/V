import os
import json
import urllib.request
import urllib.parse

# =========================
# الإعدادات
# =========================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

WEB_APP_URL = "https://v-alyo.vercel.app/"

TARGET_USERNAME = "@OM_G9"

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# =========================
# Telegram API
# =========================

def telegram(method, data=None):
    if not BOT_TOKEN:
        return {
            "ok": False,
            "error": "BOT_TOKEN is missing"
        }

    if data is None:
        data = {}

    try:
        encoded = urllib.parse.urlencode(data).encode("utf-8")

        request = urllib.request.Request(
            f"{API_URL}/{method}",
            data=encoded,
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            method="POST"
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


# =========================
# إرسال رسالة البداية
# =========================

def send_start(chat_id):

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🎁 إرسال هدية",
                    "web_app": {
                        "url": WEB_APP_URL
                    }
                }
            ]
        ]
    }

    text = (
        "🎁 أهلاً بك في بوت الهدايا\n\n"
        f"يمكنك اختيار قيمة الهدية وإرسالها إلى {TARGET_USERNAME}\n\n"
        "⭐ اختر إرسال هدية للمتابعة."
    )

    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": json.dumps(
                keyboard,
                ensure_ascii=False
            )
        }
    )


# =========================
# معالجة التحديثات
# =========================

def handle_update(update):

    if not isinstance(update, dict):
        return

    message = update.get("message")

    if not message:
        return

    chat = message.get("chat")

    if not chat:
        return

    chat_id = chat.get("id")

    if not chat_id:
        return

    text = message.get("text", "")

    if text.startswith("/start"):
        send_start(chat_id)
        return

    if text.startswith("/help"):

        telegram(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": (
                    "🎁 بوت الهدايا\n\n"
                    "اضغط الزر التالي لاختيار قيمة الهدية:"
                ),
                "reply_markup": json.dumps(
                    {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "🎁 إرسال هدية",
                                    "web_app": {
                                        "url": WEB_APP_URL
                                    }
                                }
                            ]
                        ]
                    },
                    ensure_ascii=False
                )
            }
        )

        return


# =========================
# Vercel Handler
# =========================

def handler(request):

    # -------------------------
    # GET
    # -------------------------

    if request.method == "GET":

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json; charset=utf-8"
            },
            "body": json.dumps(
                {
                    "ok": True,
                    "service": "Telegram Gift Demo",
                    "web_app": WEB_APP_URL,
                    "target": TARGET_USERNAME
                },
                ensure_ascii=False
            )
        }

    # -------------------------
    # POST - Telegram Webhook
    # -------------------------

    if request.method == "POST":

        try:

            body = request.body

            if isinstance(body, bytes):
                body = body.decode("utf-8")

            update = json.loads(body)

            handle_update(update)

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "ok": True
                })
            }

        except Exception as e:

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "ok": False,
                    "error": str(e)
                })
            }

    # -------------------------
    # Method غير مدعوم
    # -------------------------

    return {
        "statusCode": 405,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "ok": False,
            "error": "Method Not Allowed"
        })
    }

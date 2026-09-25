import os
import json
import urllib.request
import urllib.parse


BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

WEB_APP_URL = "https://v-alyo.vercel.app/"
TARGET_USERNAME = "@OM_G9"

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def telegram(method, data=None):
    if not BOT_TOKEN:
        return {
            "ok": False,
            "description": "BOT_TOKEN is missing"
        }

    if data is None:
        data = {}

    try:
        encoded = urllib.parse.urlencode(data).encode("utf-8")

        req = urllib.request.Request(
            f"{API_URL}/{method}",
            data=encoded,
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except Exception as e:
        return {
            "ok": False,
            "description": str(e)
        }


def send_message(chat_id, text):
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

        send_message(
            chat_id,
            (
                "🎁 أهلاً بك في بوت الهدايا\n\n"
                f"🎯 المستلم: {TARGET_USERNAME}\n\n"
                "⭐ اختر قيمة الهدية من الزر التالي:"
            )
        )

        return

    if text.startswith("/help"):

        send_message(
            chat_id,
            (
                "🎁 بوت الهدايا\n\n"
                "اضغط على «إرسال هدية» لفتح واجهة الهدايا."
            )
        )

        return


def handler(request):

    try:

        # GET
        if request.method == "GET":

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "ok": True,
                    "message": "Telegram webhook is running",
                    "web_app": WEB_APP_URL,
                    "target": TARGET_USERNAME
                }, ensure_ascii=False)
            }

        # POST
        if request.method == "POST":

            body = request.body

            if isinstance(body, bytes):
                body = body.decode("utf-8")

            if not body:
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "ok": True
                    })
                }

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

import os
import json
import urllib.request
import urllib.parse

from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

WEB_APP_URL = "https://v-alyo.vercel.app/"
TARGET_USERNAME = "@OM_G9"

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


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

        req = urllib.request.Request(
            f"{API_URL}/{method}",
            data=encoded,
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


def gift_keyboard():
    return {
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


def send_start(chat_id):

    text = (
        "🎁 أهلاً بك في بوت الهدايا\n\n"
        f"يمكنك اختيار قيمة الهدية وإرسالها إلى {TARGET_USERNAME}\n\n"
        "⭐ اضغط على الزر بالأسفل للمتابعة."
    )

    result = telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": json.dumps(
                gift_keyboard(),
                ensure_ascii=False
            )
        }
    )

    return result


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
                    "اضغط الزر بالأسفل لاختيار قيمة الهدية:"
                ),
                "reply_markup": json.dumps(
                    gift_keyboard(),
                    ensure_ascii=False
                )
            }
        )

        return


@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "ok": True,
        "service": "Telegram Gift Bot",
        "web_app": WEB_APP_URL,
        "target": TARGET_USERNAME
    })


@app.route("/", methods=["POST"])
def webhook():

    try:

        update = request.get_json(silent=True)

        if not update:
            return jsonify({
                "ok": False,
                "error": "Empty update"
            }), 400

        handle_update(update)

        return jsonify({
            "ok": True
        }), 200

    except Exception as e:

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 200

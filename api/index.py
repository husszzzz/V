import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

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

        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = json.dumps(
            keyboard,
            ensure_ascii=False
        )

    return telegram("sendMessage", data)


def main_keyboard():

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
                f"🎯 الهدية مخصصة إلى {TARGET_USERNAME}\n\n"
                "⭐ اضغط الزر بالأسفل لاختيار قيمة الهدية."
            ),
            main_keyboard()
        )

        return

    if text.startswith("/help"):

        send_message(
            chat_id,
            "🎁 اختر من الزر التالي:",
            main_keyboard()
        )

        return


class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):

        body = json.dumps(
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
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(body)


    def do_GET(self):

        self.send_json({
            "ok": True,
            "service": "Telegram Gift Bot",
            "status": "online",
            "telegram": "webhook",
            "web_app": WEB_APP_URL
        })


    def do_POST(self):

        try:

            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            raw = self.rfile.read(length)

            update = json.loads(
                raw.decode("utf-8")
            )

            handle_update(update)

            self.send_json({
                "ok": True
            })

        except Exception as e:

            self.send_json({
                "ok": False,
                "error": str(e)
            }, 200)


handler = Handler

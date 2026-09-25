import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEB_APP_URL = "https://v-alyo.vercel.app/"
TARGET_USERNAME = "@OM_G9"


def telegram(method, data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    body = json.dumps(data, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def send_message(chat_id):

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

    telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": (
                "🎁 أهلاً بك في بوت الهدايا\n\n"
                f"يمكنك اختيار قيمة الهدية وإرسالها إلى {TARGET_USERNAME}\n\n"
                "⭐ اضغط على الزر بالأسفل للمتابعة."
            ),
            "reply_markup": json.dumps(
                keyboard,
                ensure_ascii=False
            )
        }
    )


def process_update(update):

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

        send_message(chat_id)

    elif text.startswith("/help"):

        send_message(chat_id)


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

        self.send_json(
            {
                "ok": True,
                "service": "Telegram Gift Bot",
                "web_app": WEB_APP_URL
            }
        )

    def do_POST(self):

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

            process_update(update)

            self.send_json(
                {
                    "ok": True
                }
            )

        except Exception as e:

            self.send_json(
                {
                    "ok": False,
                    "error": str(e)
                },
                500
            )

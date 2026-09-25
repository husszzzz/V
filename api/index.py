import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()


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
        data["reply_markup"] = {
            "inline_keyboard": keyboard
        }

    return telegram("sendMessage", data)


def handle_update(update):

    message = update.get("message")

    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text.startswith("/start"):

        keyboard = [
            [
                {
                    "text": "🎁 إرسال هدية إلى @OM_G9",
                    "url": "https://t.me/OM_G9"
                }
            ]
        ]

        send_message(
            chat_id,

            "⭐ تجربة إرسال Stars\n\n"
            "إذا تريد إرسال هدية/Stars إلى حسابي الشخصي:\n"
            "@OM_G9\n\n"
            "اضغط الزر بالأسفل لفتح الحساب.",

            keyboard
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

        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api":

            self.send_json({
                "ok": True,
                "service": "Personal Stars Test Bot",
                "recipient": "@OM_G9"
            })

            return

        self.send_json({
            "ok": False,
            "error": "Not Found"
        }, 404)


    def do_POST(self):

        parsed = urllib.parse.urlparse(self.path)

        if parsed.path != "/api":

            self.send_json({
                "ok": False,
                "error": "Not Found"
            }, 404)

            return

        try:

            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            body = self.rfile.read(length)

            update = json.loads(
                body.decode("utf-8")
            )

            handle_update(update)

            self.send_json({
                "ok": True
            })

        except Exception as e:

            self.send_json({
                "ok": False,
                "error": str(e)
            }, 500)

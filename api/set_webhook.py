"""
Vercel Endpoint — Set Telegram Webhook
Visit: https://YOUR-VERCEL-URL/api/set_webhook

Automatically sets the webhook to https://YOUR-VERCEL-URL/api/webhook
"""
from http.server import BaseHTTPRequestHandler
import json
import asyncio
import sys
import os
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TELEGRAM_BOT_TOKEN = "8352132120:AAFGtA_ChS-diB3NNYXeDUsRCqP7QFHmvCc"


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        host = self.headers.get("Host", "")
        webhook_url = f"https://{host}/api/webhook"

        async def run():
            from aiogram import Bot
            b = Bot(token=TELEGRAM_BOT_TOKEN)
            await b.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query", "inline_query"]
            )
            info = await b.get_webhook_info()
            await b.session.close()
            return {
                "ok": True,
                "webhook_set": webhook_url,
                "pending_updates": info.pending_update_count,
                "last_error": info.last_error_message or None,
            }

        result = asyncio.run(run())

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result, indent=2).encode())

    def log_message(self, format, *args):
        pass

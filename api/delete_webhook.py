"""
Vercel Endpoint — Delete Telegram Webhook
Visit: https://YOUR-VERCEL-URL/api/delete_webhook

Use this before switching back to polling mode (local/Replit).
"""
from http.server import BaseHTTPRequestHandler
import json
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TELEGRAM_BOT_TOKEN = "8352132120:AAFGtA_ChS-diB3NNYXeDUsRCqP7QFHmvCc"


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        async def run():
            from aiogram import Bot
            b = Bot(token=TELEGRAM_BOT_TOKEN)
            await b.delete_webhook(drop_pending_updates=True)
            await b.session.close()
            return {"ok": True, "action": "webhook_deleted"}

        result = asyncio.run(run())

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result, indent=2).encode())

    def log_message(self, format, *args):
        pass

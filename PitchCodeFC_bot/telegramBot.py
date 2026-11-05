import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        raise ValueError("Telegram credentials are missing.")

    bot = Bot(token=BOT_TOKEN)
    chunk_size = 4000

    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        await bot.send_message(chat_id=CHAT_ID, text=chunk)

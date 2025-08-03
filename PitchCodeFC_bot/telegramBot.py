import asyncio
from telegram import Bot

BOT_TOKEN = '8154995039:AAFhWvCaWus5VkA5QJFUZ6ar20vsuNUy9tc'  # token
CHAT_ID = -1002786394948  # chat ID

async def send_telegram_message(text):
    bot = Bot(token=BOT_TOKEN)
    chunk_size = 4000  # Telegram message size limit safeguard
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size]
        await bot.send_message(chat_id=CHAT_ID, text=chunk)

import asyncio
from telegram import Bot

BOT_TOKEN = '8154995039:AAFhWvCaWus5VkA5QJFUZ6ar20vsuNUy9tc'  # Replace with your bot token
CHAT_ID = -1002786394948  # Replace with the chat ID you got earlier

async def send_message():
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text="🚨 Bot is live! This is a test alert.")

if __name__ == '__main__':
    asyncio.run(send_message())

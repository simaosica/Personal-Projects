import asyncio
from telegram import Bot

BOT_TOKEN = '8154995039:AAFhWvCaWus5VkA5QJFUZ6ar20vsuNUy9tc'  # replace this with your token

async def get_chat_id():
    bot = Bot(token=BOT_TOKEN)
    updates = await bot.get_updates()
    for u in updates:
        if u.message:
            print("Chat ID:", u.message.chat.id)
            print("Chat Title:", u.message.chat.title)

if __name__ == '__main__':
    asyncio.run(get_chat_id())

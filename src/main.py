import asyncio
import re

from telebot.async_telebot import AsyncTeleBot
from llms import respond_deepseek


bot = AsyncTeleBot("7259345100:AAFNgQ0qK4ziQBheHPMu-ly-YoyUhXzOzt0")


sessions = {}


def process_name(name: str) -> str:
    if name is None:
        return ""
    else:
        return name


@bot.message_handler(commands=['start', 'help'])
async def send_welcome(message):
    await bot.reply_to(
        message,
        "Hi! Send me a message or a chat with someone,"
        " type '/submit' and I'll tell you what they were thinking!"
    )


@bot.message_handler(func=lambda message: True)
async def echo_all(message):
    user_id = message.from_user.id
    if user_id not in sessions:
        sessions[user_id] = []
    if message.text == "/submit":
        messages = sessions[user_id]
        messages = sorted(messages, key=lambda m: m.date)
        origins = []
        for i in messages:
            if i.forward_from is not None:
                origins.append(i.forward_from.full_name)
            elif i.forward_sender_name is not None:
                origins.append(i.forward_sender_name)
            else:
                origins.append("UNKNOWN")
        texts = [i.text for i in messages]
        messages = [f"{i}: {j}" for i, j in zip(origins, texts)]
        messages = "\n".join(messages)
        output = await respond_deepseek(messages)
        output = re.sub("\n+", "\n", output)
        output = output.split("\n")
        for i in output:
            await bot.reply_to(message, i[:4095])
        del sessions[user_id]
    else:
        sessions[user_id].append(message)


if __name__ == '__main__':
    asyncio.run(bot.infinity_polling())

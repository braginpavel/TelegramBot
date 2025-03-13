import json
import re

import aiohttp
import asyncpg
from telebot.async_telebot import AsyncTeleBot
from telebot import formatting

from conf.config import (BACKEND_HOST, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT,
                         DB_USER, WHAT_SHE_THINKS_KEY)

bot = AsyncTeleBot(WHAT_SHE_THINKS_KEY)


class Pool:
    def __init__(self):
        self._pool = None

    async def get_pool(self):
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                host=DB_HOST,
                port=DB_PORT,
                min_size=10,
                max_size=70,
            )
            return self._pool
        else:
            return self._pool

pool_provider = Pool()

def process_name(name: str) -> str:
    if name is None:
        return ""
    else:
        return name


@bot.message_handler(commands=["start", "help"])
async def send_welcome1(message):
    first_name = process_name(message.from_user.first_name)
    last_name = process_name(message.from_user.last_name)
    telegram_id = message.from_user.id
    data = {
        "first_name": first_name,
        "last_name": last_name,
        "telegram_id": telegram_id,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_HOST}/thoughts/register", json=data
        ) as response:
            _ = await response.json()
    await bot.reply_to(
        message,
        formatting.format_text(formatting.mbold("""Hi! Want to know how to use the bot?
1. Send or forward any telegram messages or chats here.
2. The bot will let you know when they are processed."""),
formatting.mitalic("""If it's a group chat, the bot will check what the last person said. Captioned photos and videos will not be processed correctly"""),
formatting.mbold("""3. When you're done, tap the bot menu button near the message field. 
4. Press /submit to get a quick summary of hidden thoughts.
5. Then, press /details to see the full thought process behind the messages."""))
        , separator=" ", parse_mode='MarkdownV2'
    )


@bot.message_handler(commands=["submit"])
async def send_welcome2(message):
    first_name = process_name(message.from_user.first_name)
    last_name = process_name(message.from_user.last_name)
    telegram_id = message.from_user.id
    await bot.reply_to(
        message,
        "Okay, I'm on it! You're in line. "
        "I'll send you a notification once I'm "
        "done—usually in about a minute!",
    )
    data = {
        "telegram_id": telegram_id,
        "first_name": first_name,
        "last_name": last_name,
    }
    print("Sending request")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_HOST}/thoughts/get_thoughts", json=data
        ) as response:
            response = await response.json()
    response = re.sub("[*]", "", response)
    await bot.reply_to(message, response)


@bot.message_handler(commands=["details"])
async def send_welcome3(message):
    first_name = process_name(message.from_user.first_name)
    last_name = process_name(message.from_user.last_name)
    telegram_id = message.from_user.id
    data = {
        "telegram_id": telegram_id,
        "first_name": first_name,
        "last_name": last_name,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_HOST}/thoughts/get_think_details", json=data
        ) as response:
            output = await response.json()
    output = re.sub("<think>\n*", "", output)
    output = re.sub("\n*</think>", "", output)
    output = re.sub("\n+", "\n", output)
    output = output.split("\n")
    for num, i in enumerate(output):
        if num == 0:
            continue
        await bot.reply_to(message, i[:4095])


@bot.message_handler(func=lambda message: True)
async def echo_all(message):
    first_name = process_name(message.from_user.first_name)
    last_name = process_name(message.from_user.last_name)
    telegram_id = message.from_user.id

    if message.forward_from is not None:
        sender_name = message.forward_from.full_name
    elif message.forward_sender_name is not None:
        sender_name = message.forward_sender_name
    else:
        sender_name = (
            message.from_user.first_name + " " + message.from_user.last_name
        )
    sender_id = "0"
    message_text = message.text
    data = {
        "telegram_id": telegram_id,
        "sender_name": sender_name,
        "sender_id": sender_id,
        "first_name": first_name + " " + last_name,
        "last_name": last_name,
        "message_text": message_text,
        "message_id": message.message_id,
    }
    data = json.dumps(data)
    data = re.sub("'", "''", data)
    query = f"""
    UPDATE thought_analysis_thoughtsession
    SET messages = messages || '{data}'::jsonb,
        n_messages = n_messages + 1
    where telegram_id = {telegram_id}
    """
    pool = await pool_provider.get_pool()
    async with pool.acquire() as connection:
        _ = await connection.execute(query)
    await bot.reply_to(message, "Message processed")

import asyncio
import json
import os
import re

import aiohttp
import psycopg_pool
from telebot.async_telebot import AsyncTeleBot

from conf.config import (BACKEND_HOST, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT,
                         DB_USER, WHAT_SHE_THINKS_KEY)

bot = AsyncTeleBot(WHAT_SHE_THINKS_KEY)
conninfo = (
    f'host={DB_HOST} '
    f'port={DB_PORT} '
    f'dbname={DB_NAME} '
    f'user={DB_USER} '
    f'password={DB_PASSWORD}'
)
pool = psycopg_pool.AsyncConnectionPool(conninfo=conninfo, open=False)


async def open_pool():
    await pool.open()
    await pool.wait()
    print("Connection Pool Opened")


asyncio.run(open_pool())


def process_name(name: str) -> str:
    if name is None:
        return ""
    else:
        return name


@bot.message_handler(commands=["start", "help"])
async def send_welcome(message):
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
        "Hi! Send me a message or a chat with someone,"
        " type '/submit' and I'll tell you what they were thinking!",
    )


@bot.message_handler(commands=["submit"])
async def send_welcome(message):
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


@bot.message_handler(commands=["full_thought"])
async def send_welcome(message):
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
    for i in output:
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
        "message_id": message.message_id
    }
    data = json.dumps(data)
    data = re.sub("'", "''", data)
    query = f"""
    UPDATE thought_analysis_thoughtsession
    SET messages = messages || '{data}'::jsonb,
        n_messages = n_messages + 1
    where telegram_id = {telegram_id}
    """
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query)

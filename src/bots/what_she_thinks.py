import json
import re

import aiohttp
import asyncpg
from telebot.async_telebot import AsyncTeleBot
from telebot import formatting
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

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
    
    # Create inline keyboard markup
    markup = InlineKeyboardMarkup()
    # Add buttons in a row
    markup.row(
        InlineKeyboardButton("Submit", callback_data="submit"),
        InlineKeyboardButton("Details", callback_data="details")
    )
    # Add another button in a new row
    markup.add(InlineKeyboardButton("Help", callback_data="help"))
    
    await bot.reply_to(
        message,
"""Hi! Want to know how to use the bot?
1. Send or forward any telegram messages or chats here.
2. The bot will let you know when they are processed.
If it's a group chat, the bot will check what the last person said. Captioned photos and videos will not be processed correctly
3. When you're done, tap the bot menu button near the message field. 
4. Press /submit to get a quick summary of hidden thoughts.
5. Then, press /details to see the full thought process behind the messages.""",
        reply_markup=markup
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
        
        # Get current message count
        query = f"SELECT n_messages FROM thought_analysis_thoughtsession WHERE telegram_id = {telegram_id}"
        n_messages = await connection.fetchval(query)
    
    # Basic message processing notification
    await bot.reply_to(message, "Message processed")
    
    # After 3 messages, suggest actions with a reply keyboard
    if n_messages and n_messages % 3 == 0:
        # Create a custom keyboard
        markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(
            KeyboardButton("Submit Analysis"),
            KeyboardButton("View Details"),
            KeyboardButton("Help"),
            KeyboardButton("Start Over")
        )
        
        await bot.send_message(
            message.chat.id,
            "I've processed a few messages. Would you like to see the analysis?",
            reply_markup=markup
        )


# Handler for reply keyboard responses
@bot.message_handler(func=lambda message: message.text in ["Submit Analysis", "View Details", "Help", "Start Over"])
async def handle_keyboard_reply(message):
    """Handle responses from the custom keyboard"""
    telegram_id = message.from_user.id
    first_name = process_name(message.from_user.first_name)
    last_name = process_name(message.from_user.last_name)
    
    if message.text == "Submit Analysis":
        # Similar to the "submit" callback
        await bot.send_message(
            telegram_id,
            "Okay, I'm on it! You're in line. "
            "I'll send you a notification once I'm "
            "done—usually in about a minute!"
        )
        data = {
            "telegram_id": telegram_id,
            "first_name": first_name,
            "last_name": last_name,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_HOST}/thoughts/get_thoughts", json=data
            ) as response:
                response = await response.json()
        response = re.sub("[*]", "", response)
        await bot.send_message(telegram_id, response)
    
    elif message.text == "View Details":
        # Similar to the "details" callback
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
            await bot.send_message(telegram_id, i[:4095])
    
    elif message.text == "Help":
        # Send help message
        await bot.send_message(
            telegram_id,
            "This bot analyzes messages to reveal hidden thoughts. "
            "Forward messages to analyze them, then use Submit Analysis and View Details to see results."
        )
    
    elif message.text == "Start Over":
        # Reset the session
        query = f"""
        UPDATE thought_analysis_thoughtsession
        SET messages = '[]'::jsonb,
            n_messages = 0
        WHERE telegram_id = {telegram_id}
        """
        pool = await pool_provider.get_pool()
        async with pool.acquire() as connection:
            _ = await connection.execute(query)
        
        # Remove keyboard
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Send me a message to analyze"))
        
        await bot.send_message(
            telegram_id, 
            "Session reset. You can now send new messages for analysis.",
            reply_markup=markup
        )


# Handler for button clicks (callback queries)
@bot.callback_query_handler(func=lambda call: True)
async def handle_callback_query(call):
    """Handle callback queries from inline keyboard buttons"""
    telegram_id = call.from_user.id
    first_name = process_name(call.from_user.first_name)
    last_name = process_name(call.from_user.last_name)
    
    # Answer the callback query to remove the "loading" state
    await bot.answer_callback_query(call.id)
    
    if call.data == "submit":
        # Replicate functionality from send_welcome2
        await bot.send_message(
            telegram_id,
            "Okay, I'm on it! You're in line. "
            "I'll send you a notification once I'm "
            "done—usually in about a minute!"
        )
        data = {
            "telegram_id": telegram_id,
            "first_name": first_name,
            "last_name": last_name,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_HOST}/thoughts/get_thoughts", json=data
            ) as response:
                response = await response.json()
        response = re.sub("[*]", "", response)
        await bot.send_message(telegram_id, response)
    
    elif call.data == "details":
        # Replicate functionality from send_welcome3
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
            await bot.send_message(telegram_id, i[:4095])
    
    elif call.data == "help":
        # Send help message
        await bot.send_message(
            telegram_id,
            "This bot analyzes messages to reveal hidden thoughts. "
            "Forward messages to analyze them, then use Submit and Details buttons to see results."
        )

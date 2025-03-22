import json
import re

import aiohttp
import asyncpg
from telebot.async_telebot import AsyncTeleBot
from telebot import formatting
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException

from conf.config import (BACKEND_HOST, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT,
                         DB_USER, WHAT_SHE_THINKS_KEY)

bot = AsyncTeleBot(WHAT_SHE_THINKS_KEY)

# Dictionary to track messages to clean up, keyed by user ID
user_messages = {}

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

# Helper function to delete previous bot messages
async def delete_previous_messages(user_id, chat_id):
    if user_id in user_messages:
        message_ids = user_messages[user_id]
        for msg_id in message_ids:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except ApiTelegramException as e:
                # Message might already be deleted or too old to delete
                print(f"Could not delete message {msg_id}: {e}")
        # Clear the list after attempting to delete all messages
        user_messages[user_id] = []


@bot.message_handler(commands=["start", "help"])
async def send_welcome1(message):
    # Clean up previous messages
    await delete_previous_messages(message.from_user.id, message.chat.id)
    
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
    sent_msg = await bot.reply_to(
        message,
"""Hi! Want to know how to use the bot?
1. Send or forward any telegram messages or chats here.
2. The bot will let you know when they are processed.
If it's a group chat, the bot will check what the last person said. Captioned photos and videos will not be processed correctly
3. When you're done, tap the bot menu button near the message field. 
4. Press /submit to get a quick summary of hidden thoughts.
5. Then, press /details to see the full thought process behind the messages."""
    )
    
    # # Store sent message ID for potential cleanup later
    # if telegram_id not in user_messages:
    #     user_messages[telegram_id] = []
    # user_messages[telegram_id].append(sent_msg.message_id)


@bot.message_handler(commands=["submit"])
async def send_welcome2(message):
    # Clean up previous messages
    await delete_previous_messages(message.from_user.id, message.chat.id)
    
    first_name = process_name(message.from_user.first_name)
    last_name = process_name(message.from_user.last_name)
    telegram_id = message.from_user.id
    sent_msg = await bot.reply_to(
        message,
        "Okay, I'm on it! You're in line. "
        "I'll send you a notification once I'm "
        "done—usually in about a minute!",
    )
    
    # Store sent message ID
    if telegram_id not in user_messages:
        user_messages[telegram_id] = []
    # user_messages[telegram_id].append(sent_msg.message_id)
    
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
    # Create inline keyboard with buttons for the response message
    details_markup = InlineKeyboardMarkup()
    details_button = InlineKeyboardButton("Uncover more details", callback_data="details")
    start_button = InlineKeyboardButton("Go to start", callback_data="add")
    details_markup.row(details_button, start_button)

    # Send the response with the inline buttons
    sent_msg = await bot.reply_to(message, response, reply_markup=details_markup)
    # user_messages[telegram_id].append(sent_msg.message_id)


@bot.message_handler(commands=["details"])
async def send_welcome3(message):
    # Clean up previous messages
    await delete_previous_messages(message.from_user.id, message.chat.id)
    
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
    
    # Store all sent message IDs
    if telegram_id not in user_messages:
        user_messages[telegram_id] = []
        
    for num, i in enumerate(output):
        if num == 0:
            continue
        sent_msg = await bot.reply_to(message, i[:4095])
        # user_messages[telegram_id].append(sent_msg.message_id)


@bot.message_handler(func=lambda message: True)
async def echo_all(message):
    # Clean up previous messages if this is a new user message
    await delete_previous_messages(message.from_user.id, message.chat.id)
    
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
    
    # Create inline keyboard with buttons
    markup = InlineKeyboardMarkup()
    submit_button = InlineKeyboardButton("Submit", callback_data="submit")
    add_button = InlineKeyboardButton("Add message", callback_data="add")
    markup.row(submit_button, add_button)
    
    # Send reply and store the message ID
    sent_msg = await bot.reply_to(message, "Message processed. What would you like to do next?", reply_markup=markup)
    
    # Store sent message ID for potential cleanup later
    if telegram_id not in user_messages:
        user_messages[telegram_id] = []
    user_messages[telegram_id].append(sent_msg.message_id)

# Handle callback queries from inline buttons
@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    # Get user ID for message tracking
    telegram_id = call.from_user.id
    chat_id = call.message.chat.id
    
    # Answer the callback query to remove the loading state
    await bot.answer_callback_query(call.id)
    
    # Remove the inline keyboard after user clicks a button
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=None
    )
    
    # Clean up previous messages except the one that was just clicked
    current_msg_id = call.message.message_id
    if telegram_id in user_messages:
        message_ids = [msg_id for msg_id in user_messages[telegram_id] if msg_id != current_msg_id]
        for msg_id in message_ids:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except ApiTelegramException as e:
                print(f"Could not delete message {msg_id}: {e}")
        # Update the list to only include the current message
        user_messages[telegram_id] = [current_msg_id]
    
    # Create a proper message object for function calls
    chat_id = call.message.chat.id
    
    # Instead of directly calling the handler functions, send appropriate responses
    if call.data == "submit":
        first_name = process_name(call.from_user.first_name)
        last_name = process_name(call.from_user.last_name)
        telegram_id = call.from_user.id
        sent_msg = await bot.send_message(
            chat_id,
            "Okay, I'm on it! You're in line. "
            "I'll send you a notification once I'm "
            "done—usually in about a minute!"
        )
        # Store sent message ID
        # user_messages[telegram_id].append(sent_msg.message_id)
        
        data = {
            "telegram_id": telegram_id,
            "first_name": first_name,
            "last_name": last_name,
        }
        print("Sending submit request")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_HOST}/thoughts/get_thoughts", json=data
            ) as response:
                response = await response.json()
        response = re.sub("[*]", "", response)
        
        # Create inline keyboard with buttons for the response message
        details_markup = InlineKeyboardMarkup()
        details_button = InlineKeyboardButton("Uncover more details", callback_data="details")
        start_button = InlineKeyboardButton("Go to start", callback_data="add")
        details_markup.row(details_button, start_button)
        
        # Send the response with the inline buttons and store message ID
        sent_msg = await bot.send_message(chat_id, response, reply_markup=details_markup)
        # user_messages[telegram_id].append(sent_msg.message_id)
        
    elif call.data == "add":
        sent_msg = await bot.send_message(
            chat_id,
"""Forward here or copy any message where you want to uncover secret thoughts.
Captioned images or videos are not supported"""
        )
        # Store sent message ID
        # user_messages[telegram_id].append(sent_msg.message_id)
        
    elif call.data == "details":
        # Handle the details button click to call get_think_details API
        first_name = process_name(call.from_user.first_name)
        last_name = process_name(call.from_user.last_name)
        telegram_id = call.from_user.id
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
        
        # Delete previous messages before sending details
        await delete_previous_messages(telegram_id, chat_id)
        
        for num, i in enumerate(output):
            if num == 0:
                continue
            sent_msg = await bot.send_message(chat_id, i[:4095])
            # user_messages[telegram_id].append(sent_msg.message_id)

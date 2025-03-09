import re

import aiohttp
from telebot.async_telebot import AsyncTeleBot

from conf.config import WHAT_SHE_THINKS_KEY, BACKEND_HOST


class WhatSheThinks:
    """
    What she thinks bot
    """

    bot = AsyncTeleBot(WHAT_SHE_THINKS_KEY)

    @staticmethod
    def process_name(name: str) -> str:
        if name is None:
            return ""
        else:
            return name

    @bot.message_handler(commands=["start", "help"])
    async def send_welcome(self, message):
        await self.bot.reply_to(
            message,
            "Hi! Send me a message or a chat with someone,"
            " type '/submit' and I'll tell you what they were thinking!",
        )

    @bot.message_handler(func=lambda message: True)
    async def echo_all(self, message):
        telegram_id = message.from_user.id
        first_name = message.forward_from.full_name
        last_name = ""
        if message.text == "/submit":
            data = {
                "telegram_id": telegram_id,
                "first_name": first_name,
                "last_name": last_name,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_HOST}/get_thoughts", json=data
                ) as response:
                    response = await response.json()
            await self.bot.reply_to(message, response.data)
        elif message.text == "/full_thought":
            data = {
                "telegram_id": telegram_id,
                "first_name": first_name,
                "last_name": last_name,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_HOST}/get_think_details", json=data
                ) as response:
                    output = await response.json()
            output = re.sub("\n+", "\n", output.data)
            output = output.split("\n")
            for i in output:
                await self.bot.reply_to(message, i[:4095])
        else:
            if message.forward_from is not None:
                sender_name = message.forward_from.full_name
            elif message.forward_sender_name is not None:
                sender_name = message.forward_sender_name
            else:
                sender_name = "UNKNOWN"
            sender_id = "0"
            message_text = message.text
            data = {
                telegram_id: "telegram_id",
                sender_name: "sender_name",
                sender_id: "sender_id",
                first_name: "first_name",
                last_name: "last_name",
                message_text: "message_text",
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_HOST}/send_message", json=data
                ) as response:
                    await response.json()

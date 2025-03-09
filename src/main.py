"""
Main module
"""

import asyncio

from bots import what_she_thinks

if __name__ == "__main__":

    # What She Thinks
    bot_class_1 = what_she_thinks.WhatSheThinks()
    bot_1 = bot_class_1.bot

    # TODO: add AI girlfriend

    async with asyncio.TaskGroup() as tg:
        task_1 = tg.create_task(bot_1.infinity_polling())

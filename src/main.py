"""
Main module
"""

import asyncio
import os
import subprocess

from bots import what_she_thinks

if os.environ.get("LOCAL_RUN"):
    pass
else:
    subprocess.Popen("poetry run python -m http.server 8080", shell=True)


async def main():
    # What She Thinks
    bot_1 = what_she_thinks.bot

    # TODO: add AI girlfriend

    async with asyncio.TaskGroup() as tg:
        _ = tg.create_task(bot_1.infinity_polling())


if __name__ == "__main__":
    asyncio.run(what_she_thinks.bot.infinity_polling())

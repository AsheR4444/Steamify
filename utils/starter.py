import asyncio

from data import config
from utils.steamify import Steamify
from asyncio import sleep
from random import uniform
from aiohttp.client_exceptions import ContentTypeError
from utils.core import logger
from datetime import datetime


async def start(thread: int, session_name: str, phone_number: str, proxy: [str, None]):
    steamify = Steamify(
        session_name=session_name, phone_number=phone_number, thread=thread, proxy=proxy
    )
    account = session_name + ".session"

    await sleep(uniform(*config.DELAYS["ACCOUNT"]))
    if await steamify.login() is None:
        return

    while True:
        try:
            await asyncio.sleep(5)

            if await steamify.need_new_login():
                if await steamify.login() is None:
                    return

            is_farm_completed, start_time, end_time = await steamify.check_info()

            if is_farm_completed:
                await steamify.claim_daily_reward()
                await sleep(uniform(2, 5))
                await steamify.start_farm()
            else:
                now = datetime.now().timestamp()
                logger.info(
                    f"Thread {thread} | {account} | Sleep {int(end_time - now)} seconds!"
                )
                await sleep(int(end_time - now) + uniform(*config.DELAYS["CLAIM"]))

            await sleep(30)
        except ContentTypeError as e:
            logger.error(f"Thread {thread} | {account} | Error: {e}")
            await asyncio.sleep(120)

        except Exception as e:
            logger.error(f"Thread {thread} | {account} | Error: {e}")

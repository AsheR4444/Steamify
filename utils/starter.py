import asyncio

from data import config
from utils.steamify import Steamify
from asyncio import sleep
from random import uniform
from aiohttp.client_exceptions import ContentTypeError
from utils.core import logger
from datetime import datetime
from utils.telegram import Accounts
import pandas as pd


async def start(thread: int, session_name: str, phone_number: str, proxy: [str, None]):
    steamify = Steamify(session_name=session_name, phone_number=phone_number, thread=thread, proxy=proxy)
    account = session_name + ".session"

    await sleep(uniform(*config.DELAYS["ACCOUNT"]))
    if await steamify.login() is None:
        return

    while True:
        try:
            await steamify.random_wait()

            if await steamify.need_new_login():
                if await steamify.login() is None:
                    return

            is_farm_active, is_farm_completed, start_time, end_time = await steamify.check_info()
            await steamify.claim_daily()
            await steamify.random_wait()
            await steamify.claim_sparks()
            await steamify.random_wait()
            await steamify.play_case_game()

            if is_farm_completed:
                await steamify.claim()
                await steamify.random_wait()
                await steamify.start_farm()
            elif is_farm_active:
                now = datetime.now().timestamp()
                logger.info(f"Thread {thread} | {account} | Sleep {int(end_time - now)} seconds!")
                await sleep(end_time - now + uniform(*config.DELAYS["CLAIM"]))

        except ContentTypeError as e:
            logger.error(f"Thread {thread} | {account} | Error: {e}")
            await asyncio.sleep(120)

        except Exception as e:
            logger.error(f"Thread {thread} | {account} | Error: {e}")


async def stats():
    accounts = await Accounts().get_accounts()

    tasks = []
    for thread, account in enumerate(accounts):
        session_name, phone_number, proxy = account.values()
        tasks.append(asyncio.create_task(Steamify(session_name=session_name, phone_number=phone_number, thread=thread, proxy=proxy).stats()))

    data = await asyncio.gather(*tasks)

    path = f"statistics/statistics_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.csv"
    columns = ['Username', 'Points', 'Referral link', 'Invites used', 'Proxy (login:password@ip:port)']

    df = pd.DataFrame(data, columns=columns)
    df['Username'] = df['Username'].astype(str)
    df.to_csv(path, index=False, encoding='utf-8-sig')

    logger.success(f"Saved statistics to {path}")

import random
import datetime
from utils.core import logger
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView
import asyncio
from urllib.parse import unquote, quote
from data import config
import aiohttp
from fake_useragent import UserAgent
from aiohttp_socks import ProxyConnector


class Steamify:
    def __init__(
        self, thread: int, session_name: str, phone_number: str, proxy: [str, None]
    ):
        self.account = session_name + ".session"
        self.thread = thread
        self.proxy = (
            f"{config.PROXY_TYPES['REQUESTS']}://{proxy}" if proxy is not None else None
        )
        connector = (
            ProxyConnector.from_url(self.proxy)
            if proxy
            else aiohttp.TCPConnector(verify_ssl=False)
        )

        if proxy:
            proxy = {
                "scheme": config.PROXY_TYPES["TG"],
                "hostname": proxy.split(":")[1].split("@")[1],
                "port": int(proxy.split(":")[2]),
                "username": proxy.split(":")[0],
                "password": proxy.split(":")[1].split("@")[0],
            }

        self.client = Client(
            name=session_name,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            workdir=config.WORKDIR,
            proxy=proxy,
            lang_code="ru",
        )

        headers = {"User-Agent": UserAgent(os="android").random}
        self.session = aiohttp.ClientSession(
            headers=headers,
            trust_env=True,
            connector=connector,
            timeout=aiohttp.ClientTimeout(120),
        )

    async def need_new_login(self):
        if (
            await self.session.get("https://api.app.steamify.io/api/v1/user/me")
        ).status == 200:
            return False
        else:
            return True

    async def login(self):
        self.session.headers.pop("Authorization", None)
        query = await self.get_tg_web_data()

        if query is None:
            logger.error(
                f"Thread {self.thread} | {self.account} | Session {self.account} invalid"
            )
            await self.logout()
            return None

        self.session.headers["Authorization"] = "Bearer " + query
        return True

    async def logout(self):
        await self.session.close()

    async def claim_daily_reward(self):
        resp = await self.session.get("https://api.app.steamify.io/api/v1/farm/claim")
        is_ok = (await resp.json()).get("msg")

        if is_ok == "ok":
            logger.success(f"Thread {self.thread} | {self.account} | Claimed reward!")

    async def start_farm(self):
        resp = await self.session.get("https://api.app.steamify.io/api/v1/farm/start")
        is_ok = (await resp.json()).get("msg")

        if is_ok == "ok":
            logger.success(f"Thread {self.thread} | {self.account} | Farming started!")

    async def check_info(self):
        resp = await self.session.get("https://api.app.steamify.io/api/v1/user/me")
        start_time = (await resp.json()).get("data").get("farm").get("started_at")
        end_time = start_time + 21600
        is_farm_completed = (await resp.json()).get("data").get("farm").get(
            "status"
        ) == "completed"
        is_ok = (await resp.json()).get("msg")

        return is_farm_completed, start_time, end_time

    async def get_tg_web_data(self):
        try:
            await self.client.connect()

            web_view = await self.client.invoke(
                RequestWebView(
                    peer=await self.client.resolve_peer("steamify_bot"),
                    bot=await self.client.resolve_peer("steamify_bot"),
                    platform="android",
                    from_bot_menu=False,
                    url="https://telegram.steamify.codes/",
                )
            )
            await self.client.disconnect()

            auth_url = web_view.url

            query = unquote(
                string=unquote(
                    string=auth_url.split("tgWebAppData=")[1].split("&tgWebAppVersion")[
                        0
                    ]
                )
            )
            query_id = query.split("query_id=")[1].split("&user=")[0]
            user = quote(query.split("&user=")[1].split("&auth_date=")[0])
            auth_date = query.split("&auth_date=")[1].split("&hash=")[0]
            hash_ = query.split("&hash=")[1]

            return f"query_id={query_id}&user={user}&auth_date={auth_date}&hash={hash_}"
        except:
            return None

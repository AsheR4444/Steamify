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
from random import uniform


API_URL = "https://api.app.steamify.io/api/v1"


def retry_async(max_retries=2):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            thread, account = args[0].thread, args[0].account
            retries = 0
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    logger.error(f"Thread {thread} | {account} | Error: {e}. Retrying {retries}/{max_retries}...")
                    await asyncio.sleep(10)
                    if retries >= max_retries:
                        break

        return wrapper

    return decorator


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
        if (await self.session.get(f"{API_URL}/user/me")).status == 200:
            return False
        else:
            return True

    async def login(self):
        self.session.headers.pop("Authorization", None)
        query = await self.get_tg_web_data()

        if query is None:
            logger.error(f"Thread {self.thread} | {self.account} | Session {self.account} invalid")
            await self.logout()
            return None

        self.session.headers["Authorization"] = "Bearer " + query
        return True

    async def logout(self):
        await self.session.close()

    @retry_async()
    async def claim(self):
        resp = await self.session.get(f"{API_URL}/farm/claim")
        is_ok = (await resp.json()).get("msg")

        if is_ok == "ok":
            logger.success(f"Thread {self.thread} | {self.account} | Claimed reward!")

    @retry_async()
    async def start_farm(self):
        resp = await self.session.get(f"{API_URL}/farm/start")
        is_ok = (await resp.json()).get("msg")

        if is_ok == "ok":
            logger.success(f"Thread {self.thread} | {self.account} | Farming started!")

    @retry_async()
    async def check_info(self):
        resp = await self.session.get(f"{API_URL}/user/me")
        start_time = (await resp.json()).get("data").get("farm").get("started_at")
        farm_status = (await resp.json()).get("data").get("farm").get("status")
        is_farm_completed = farm_status == "completed"
        is_farm_active = farm_status == "in_progress"
        is_farm_available = farm_status == "available"
        end_time = None

        if not is_farm_available:
            end_time = start_time + 21600

        #is_ok = (await resp.json()).get("msg")

        return is_farm_active, is_farm_available, is_farm_completed, start_time, end_time

    @retry_async()
    async def claim_daily(self):
        resp = await self.session.get(f"{API_URL}/user/daily/claim")
        is_claimed = (await resp.json()).get("msg") == "already claimed"

        if is_claimed:
            logger.success(f"Thread {self.thread} | {self.account} | Daily reward claimed!")

        return is_claimed

    @retry_async()
    async def stats(self):
        await asyncio.sleep(random.uniform(*config.DELAYS['ACCOUNT']))
        await self.login()

        info_resp = await (await self.session.get(f"{API_URL}/user/me")).json()
        info_data = info_resp.get("data")
        await asyncio.sleep(random.uniform(3, 7))
        invites_resp = await (await self.session.get(f"{API_URL}/user/invite")).json()
        invites_data = invites_resp.get("data").get("code_data")
        invites_used = invites_data.get("used")
        invite_link = invites_data.get("link")
        balance = info_data.get("balance")
        username = info_data.get("username")
        proxy = self.proxy.replace('http://', "") if self.proxy is not None else '-'

        await self.logout()

        return [username, balance, invite_link, invites_used, proxy]
    
    async def claim_sparks(self):
        resp = await self.session.get(f"{API_URL}/game/case/inventory/claim")
        data = await resp.json()
        sparks = data.get("data").get("claimed_sparks")

        logger.success(f"Thread {self.thread} | {self.account} | {sparks} sparks claimed!")
        
    @retry_async()
    async def play_case_game(self):
        if not config.CASE_OPEN_GAME['PLAY']:
            return

        logger.info(f"Thread {self.thread} | {self.account} | Playing case game...")

        max_plays = random.randint(*config.CASE_OPEN_GAME['CASES_TO_BE_OPENED'])
        logger.info(f"Thread {self.thread} | {self.account} | Going to open {max_plays} cases...")
        await self.random_wait()

        plays = 0

        while plays < max_plays:
            balance, claimable, farm_status, started_at, total_duration = await self.get_status()

            if balance < config.CASE_OPEN_GAME['MIN_BALANCE_CONTROL']:
                logger.warning(f"Thread {self.thread} | {self.account} | Current balance ({balance}) is lower than minimal defined in config ({config.CASE_OPEN_GAME['MIN_BALANCE_CONTROL']}), skipping playing...")
                return

            await self.random_wait()
            cases = await self.list_cases()

            selected_case = self.select_random_case_with(cases)
            logger.info(f"Thread {self.thread} | {self.account} | Selected case to open: '{selected_case['name']}', price: ${selected_case['price']}")

            await self.random_wait()
            weapon = await self.open_case(selected_case)
            logger.info(f"Thread {self.thread} | {self.account} | plays = {plays}")
            logger.success(f"Thread {self.thread} | {self.account} | Opened a new case ({plays + 1} out of {max_plays}) | Weapon: {weapon.get('name')} | Rarity: {weapon.get('rarity')} | Is rare special item: {weapon.get('is_rare_special_item')}")
            plays += 1
            await asyncio.sleep(uniform(*config.CASE_OPEN_GAME['DELAY_BETWEEN_OPENINGS']))

    async def open_case(self, case):
        logger.info(f"Thread {self.thread} | {self.account} | Opening case '{case['name']}'...")
        resp = await self.session.post(f"{API_URL}/game/case/{case['id']}/open", json={'count':1})

        if (resp.status != 200):
            resp_text = await resp.text()
            raise Exception(f"couldn't open case: {resp_text}")

        resp_json = await resp.json()
        return resp_json.get('data')[0]

    def select_random_case_with(self, price_dict):
        min_price, max_price = config.CASE_OPEN_GAME['CASE_PRICE']
        filtered_items = {k: v for k, v in price_dict.items() if min_price <= k <= max_price}

        if not filtered_items:
            raise ValueError("No cases available that match within the given price range. Check your config")

        random_price = random.choice(list(filtered_items.keys()))
        return filtered_items[random_price]

    async def list_cases(self):
        logger.info(f"Thread {self.thread} | {self.account} | Loading cases...")
        resp = await self.session.get(f'{API_URL}/game/case/list')
        resp_json = await resp.json()

        if resp.status != 200:
            resp_text = await resp.text()
            raise Exception(f"error while playing cases: {resp_text}")

        data = resp_json.get('data')
        price_dict = {item["price"]: {"id": item["id"], "name": item["name"], "price": item["price"]} for item in data}

        return dict(sorted(price_dict.items()))

    async def get_status(self):
        resp = await self.session.get(f'{API_URL}/user/me')
        resp_json = await resp.json()

        if (resp.status != 200):
            resp_text = await resp.text()
            raise Exception(f"couldn't update account status: {resp_text}")

        return int(resp_json.get('data').get('points')), int(
            resp_json.get('data').get('farm').get('base_rewards')), resp_json.get('data').get('farm').get(
            'status'), resp_json.get('data').get('farm').get(
            'started_at'), resp_json.get('data').get('farm').get(
            'total_duration') if resp_json.get("success") else await resp.text()

    async def random_wait(self):
        await asyncio.sleep(uniform(2, 20))

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

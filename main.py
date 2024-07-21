import asyncio
import os
from utils.starter import start
from utils.telegram import Accounts


async def main():
    if not os.path.exists("sessions"):
        os.mkdir("sessions")
    if not os.path.exists("statistics"):
        os.mkdir("statistics")
    if not os.path.exists("sessions/accounts.json"):
        with open("sessions/accounts.json", "w") as f:
            f.write("[]")

    
    accounts = await Accounts().get_accounts()

    tasks = []
    for thread, account in enumerate(accounts):
        session_name, phone_number, proxy = account.values()
        tasks.append(
            asyncio.create_task(
                start(
                    session_name=session_name,
                    phone_number=phone_number,
                    thread=thread,
                    proxy=proxy,
                )
            )
        )

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

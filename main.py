import asyncio
import os
from utils.core.register import create_sessions
from utils.starter import start, stats
from utils.telegram import Accounts


async def main():
    if not os.path.exists("sessions"):
        os.mkdir("sessions")
    if not os.path.exists("statistics"):
        os.mkdir("statistics")
    if not os.path.exists("sessions/accounts.json"):
        with open("sessions/accounts.json", "w") as f:
            f.write("[]")

    action = int(input("Select action:\n1. Start soft\n2. Get statistics\n3. Create sessions\n\n> "))

    if action == 3:
        await create_sessions()

    if action == 2:
        await stats()

    if action == 1:
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

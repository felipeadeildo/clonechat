import asyncio

from utils import get_args
from utils import get_client


async def main():
    args = get_args()
    client = await get_client()
    me = await client.get_me()
    print("Bem vindo, {}".format(getattr(me, "first_name")))


if __name__ == "__main__":
    asyncio.run(main())

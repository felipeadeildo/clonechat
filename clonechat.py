import asyncio

from utils import get_args
from utils import get_chat
from utils import get_client


async def main():
    args = get_args()
    target_id, output_id = args.i, args.o
    client = await get_client()

    target = await get_chat(client)(target_id)
    output = await get_chat(client)(output_id)
    print(f"Target: {target.title}")
    print(f"Output: {output.title}")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio

from telethon import TelegramClient
from telethon.tl.patched import Message

from utils import get_args
from utils import get_chat
from utils import get_client


class CloneChat:
    """Controller for CloneChat
    
    Methods:
        clone(self): Clone Target Chat to Output Chat
    """

    def __init__(self, client: TelegramClient, target_id: int, output_id: int):
        self.client = client
        self.target_id = target_id
        self.output_id = output_id

    async def __get_chats(self):
        """Initialize Target and Output Chat"""
        self.target = await get_chat(self.client, self.target_id)
        self.output = await get_chat(self.client, self.output_id)
        del self.target_id, self.output_id

    async def clone(self):
        """Start the clonation process"""
        await self.__get_chats()
        await self.__clone_messages()

    async def __clone_message(self, message: Message):
        """Clonator wrapper method. This method decides wich method will be
            used for clonation
        
        Args:
            message (Message): The message to be cloned
        """

        clone_methods = {
            'forward': ...,
            'download': ...,
        }

        # TODO: Add conditionals to choice the clone method.

    async def __clone_messages(self):
        """Iterate over messages and call the wrapper clonator method."""
        messages = self.client.iter_messages(self.target)

        async for message in messages:
            await self.__clone_message(message)
            break


async def main():
    args = get_args()
    target_id, output_id = args.i, args.o
    client = await get_client()

    await CloneChat(client, target_id, output_id).clone()


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from pathlib import Path
from typing import Union

from telethon import TelegramClient
from telethon.tl.patched import Message

from utils import get_args
from utils import get_client
from utils import get_target


class CloneChat:
    """Controller for CloneChat
    
    Methods:
        clone(self): Clone Target Chat to Output Chat
    """

    def __init__(self, client: TelegramClient, input_id: Union[int, Path],
                 output_id: Union[int, Path]):
        """Initialize the controller

        Args:
            client (TelegramClient): The client to use for the API call.
            input_id (Union[int, Path]): if `int`: The ID of the chat to clone. 
                if `Path`: A dumpped chat folder containing dump.db file.
            output_id (Union[int, Path]): if `int`: The ID of the chat to send cloned messages.
                if `Path`: A dumpped chat to dump the chat into dump.db file.
        """
        self.client = client
        self.input_id = input_id
        self.output_id = output_id

    async def __get_targets(self):
        """Initialize Target and Output Chat"""
        self.input = await get_target(self.client, self.input_id)
        self.output = await get_target(self.client, self.output_id)

    async def clone(self):
        """Start the clonation process"""
        await self.__get_targets()
        await self.__clone_messages()

    async def __clone_messages(self):
        """Iterate over messages and call the wrapper clonator method."""

        async for message in self.input.iter_messages():
            await self.output.send_message(message)


async def main():
    args = get_args()
    input_id, output_id = args.input, args.output

    client = await get_client()

    await CloneChat(client, input_id, output_id).clone()


if __name__ == "__main__":
    asyncio.run(main())

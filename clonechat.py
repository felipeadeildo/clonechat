import asyncio
from pathlib import Path
from typing import Union

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

    async def __get_chats(self):
        """Initialize Target and Output Chat"""
        if isinstance(self.input_id, Path):
            self.input = ...
        else:
            self.input = await get_chat(self.client, self.input_id)

        if isinstance(self.output_id, Path):
            self.output = ...
        else:
            self.output = await get_chat(self.client, self.output_id)

        del self.input_id, self.output_id

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
        # TODO: Implement clonator calling the `self.target` and `self.output` methods.
        pass

    async def __clone_messages(self):
        """Iterate over messages and call the wrapper clonator method."""
        # TODO: Implement an iterator here independent of the `self.input`

        # messages = self.client.iter_messages(self.input)
        # async for message in messages:
        #     await self.__clone_message(message)
        #     break
        pass


async def main():
    args = get_args()
    input_id, output_id = args.input, args.output

    client = await get_client()

    await CloneChat(client, input_id, output_id).clone()


if __name__ == "__main__":
    asyncio.run(main())

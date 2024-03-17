import asyncio
import logging
from pathlib import Path
from typing import Union

from telethon import TelegramClient

from utils import get_args, get_client, get_target


class CloneChat:
    """Controller for CloneChat

    Methods:
        clone(self): Clone Target Chat to Output Chat
    """

    def __init__(
        self,
        client: TelegramClient,
        input_id: Union[int, Path],
        output_id: Union[int, Path],
    ):
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
        logging.debug("Initializing Targets")
        self.input = await get_target(self.client, self.input_id)
        self.output = await get_target(self.client, self.output_id, represents_chat_id=self.input_id)
        logging.debug("Targets Initialized")

    async def clone(self):
        """Start the clonation process"""
        logging.info(f"Cloning from {self.input_id} to {self.output_id}")
        await self.__get_targets()
        await self.__clone_messages()

    async def __clone_messages(self):
        """Iterate over messages and call the wrapper clonator method."""
        logging.debug(f"Walking over messages of {self.input_id}")
        async for message in self.input.iter_messages():  # type: ignore
            await self.output.send_message(message)


async def main():
    args = get_args()
    input_id, output_id = args.input, args.output

    logging.basicConfig(
        level=getattr(logging, args.loglevel.upper()),
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        handlers=[logging.StreamHandler()],
    )

    logging.getLogger("telethon").setLevel(logging.CRITICAL)

    client = await get_client()

    await CloneChat(client, input_id, output_id).clone()


if __name__ == "__main__":
    asyncio.run(main())

from abc import ABC
from abc import abstractmethod
import asyncio
from pathlib import Path
import sqlite3
from typing import AsyncGenerator, Union

from telethon import TelegramClient
from telethon.tl.types import Channel
from telethon.tl.types import Message


class UniversalMessage:
    ...


class Target(ABC):
    """Wrapper class for Target that implements some common methods for all targets."""

    def __init__(self, client: TelegramClient, target_id: Union[int, Path]):
        self.client = client
        self.target_id = target_id

    @abstractmethod
    async def iter_messages(self) -> AsyncGenerator[UniversalMessage, None]:
        """Async generator of messages [UniversalMessage]"""
        ...

    @abstractmethod
    async def send_message(self, message: UniversalMessage):
        """Send a message to save on target.

        Args:
            message (UniversalMessage): The message to send.
        """
        ...

    @abstractmethod
    def __convert_to_universal_message(self, message: Union[dict, Message]):
        """Convert a message to [UniversalMessage]

        Args:
            message (Union[dict, Message]): The message to convert. 
                Is a dict if from `DumpChat`, else from `Chat`.
        """
        ...


class Chat(Target):

    async def __init__(self, client: TelegramClient, chat_id: int):
        super().__init__(client, chat_id)
        self.target = await self.__get_telegram_chat()

    async def __get_telegram_chat(self) -> Channel:
        """Get a clonable chat entity by ID.

        Args:
            client (TelegramClient): The client to use for the API call.
            chat_id (int): The ID of the chat to clone.

        Returns:
            Channel: The clonable chat entity.
        
        Raises:
            ValueError: If the entity is not a clonable chat.
        """
        entity = await self.client.get_entity(self.target_id)  # type: ignore
        if not isinstance(entity, (Channel, )):
            raise ValueError("Entity is not Clonable Chat")
        return entity

    def __convert_to_universal_message(self, message: Union[dict, Message]):
        return super().__convert_to_universal_message(message)

    async def iter_messages(self):
        async for message in self.client.iter_messages(self.target):
            yield self.__convert_to_universal_message(message)

    async def send_message(self, message: UniversalMessage):
        return super().send_message(message)


class DumpChat(Target):

    def __init__(self, client: TelegramClient, path: Path):
        super().__init__(client, path)
        self.__dump_path = path / 'dump.db'
        if not self.__dump_path.is_file():
            self.__create_initial_schema()
        else:
            self.__set_db_connection()

    def __set_db_connection(self):
        self.__conn = sqlite3.connect(self.__dump_path)
        self.__conn.row_factory = sqlite3.Row
        self.__cursor = self.__conn.cursor()

    def __create_initial_schema(self):
        self.__set_db_connection()
        # TODO: Write a SQL script to create the schema

    def __convert_to_universal_message(self, message: dict):
        # TODO: Write the conversion (it depends of schema)
        return UniversalMessage()

    async def iter_messages(self):
        loop = asyncio.get_running_loop()
        self.__cursor.execute('SELECT * FROM messages')
        while True:
            message = await loop.run_in_executor(None, self.__cursor.fetchone)
            if message is None:
                break
            yield self.__convert_to_universal_message(message)

    async def send_message(self, message: UniversalMessage):
        return super().send_message(message)


def get_target(client: TelegramClient, target_id: Union[int, Path]) -> Target:
    """Get a target object by ID

    Args:
        client (TelegramClient): The client to use for the API call.
        target_id (Union[int, Path]): The ID of the target chat.

    Returns:
        Target: The target wrapper object.
    """
    if isinstance(target_id, Path):
        return DumpChat(client, target_id)
    else:
        return Chat(client, target_id)

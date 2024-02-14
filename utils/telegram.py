import asyncio
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncGenerator, Optional, Union

from telethon import TelegramClient
from telethon.tl.patched import MessageService
from telethon.tl.types import Channel, Message

from utils.base import create_callback

# TODO: Add Verbose on Actions (sent, iter, download, etc...)


class UniversalMessage:
    """Universal Message Representation"""

    def __init__(
        self,
        client: TelegramClient,
        chat_id: int,
        message_id: int,
        retrieve: bool = True,
        **kw
    ):
        self.client = client
        self.chat_id = chat_id
        self.message_id = message_id
        self.message: Message | None = None
        for k, v in kw.items():
            setattr(self, k, v)
        if retrieve:
            asyncio.run(self.retrieve_message())

    async def retrieve_message(self):
        _message = await self.client.get_messages(
            self.chat_id, ids=self.message_id
        )
        if _message:
            self.message = _message[0]


class Target(ABC):
    """Wrapper class for Target that implements some common methods for all targets."""

    def __init__(self, client: TelegramClient, target_id: Union[int, Path]):
        self.client = client
        self.target_id = target_id

    @abstractmethod
    async def iter_messages(self) -> AsyncGenerator[UniversalMessage, None]:
        """Async generator of messages [UniversalMessage]"""
        raise NotImplemented

    @abstractmethod
    async def send_message(self, message: UniversalMessage):
        """Send a message to save on target.

        Args:
            message (UniversalMessage): The message to send.
        """
        raise NotImplemented

    @abstractmethod
    def _get_universal_message(self, message: Union[dict, Message]):
        """Convert a message to [UniversalMessage]

        Args:
            message (Union[dict, Message]): The message to convert.
                Is a dict if from `DumpChat`, else from `Chat`.
        """
        raise NotImplemented


class TgChat(Target):

    def __init__(self, client: TelegramClient, chat_id: int, chat_entity: ...):
        super().__init__(client, chat_id)
        self.target = chat_entity

    @classmethod
    async def create(cls, client: TelegramClient, chat_id: int):
        """Create a new Chat Instance

        Args:
            client (TelegramClient): The client to use for the API call.
            chat_id (int): The ID of the chat to clone.

        Returns:
            Channel: The clonable chat entity.

        Raises:
            ValueError: If the entity is not a clonable chat.
        """
        chat_entity = await client.get_entity(chat_id)
        if not isinstance(chat_entity, (Channel,)):
            raise ValueError("Entity is not Clonable Chat")
        return cls(client, chat_id, chat_entity)

    def _get_universal_message(self, message: dict | Message):
        chat_id = int(getattr(self, "target_id"))
        if isinstance(message, dict):
            return UniversalMessage(self.client, chat_id, message["id"])
        else:
            return UniversalMessage(
                self.client,
                chat_id,
                message.id,
                retrieve=False,
                message=message,
            )

    async def iter_messages(self):
        async for message in self.client.iter_messages(self.target):
            if isinstance(message, MessageService):
                continue
            yield self._get_universal_message(message)

    async def send_message(
        self, message: UniversalMessage
    ) -> Optional[Message]:
        """Send a message to save on target.

        Args:
            message (UniversalMessage): The message to send.

        Returns:
            Message: Telegram Message Object
        """
        if not message.message:
            return

        tg_message = message.message
        save_path = (Path("chats") / str(self.target_id)) / str(tg_message.id)
        save_path.mkdir(parents=True, exist_ok=True)
        if tg_message.media:
            custom_callback = create_callback(tg_message.media)
            await self.client.download_media(
                tg_message,
                str(save_path),
                progress_callback=custom_callback,
            )
            file_path = next(p for p in save_path.iterdir() if p.is_file())
            custom_callback = create_callback(tg_message.media, "Sending")
            with open(file_path, "rb") as f:
                return await self.client.send_file(
                    self.target,
                    f,
                    caption=tg_message.message,
                    progress_callback=custom_callback,
                )
        return await self.client.send_message(self.target, message.message)


class DumpChat(Target):

    def __init__(self, client: TelegramClient, path: Path):
        super().__init__(client, path)
        self.__dump_path = path / "dump.db"
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
        schema = """
        create table if not exists messages (
            id integer primary key,
            chat_id integer,
            message_id integer,
            message_text text,
            message_media_path text
        );

        create table if not exists meta (
            id integer primary key,
            name text,
            value text
        );
        """
        self.__conn.executescript(schema)
        self.__conn.commit()
        self.chat_id = int(
            self.__conn.execute(
                "select value from meta where name = 'chat_id'"
            ).fetchone()["value"]
        )
        if self.chat_id is None:
            self.__cursor.execute(
                "insert into meta (name, value) values ('chat_id', ?)",
                (self.target_id,),
            )
            self.__conn.commit()
            self.chat_id = int(getattr(self, "target_id"))

    def _get_universal_message(self, message: dict | Message):
        if isinstance(message, dict):
            return UniversalMessage(self.client, self.chat_id, message["id"])
        else:
            return UniversalMessage(
                self.client,
                self.chat_id,
                message.id,
                retrieve=False,
                message=message,
            )

    async def iter_messages(self):
        loop = asyncio.get_running_loop()
        self.__cursor.execute("SELECT * FROM messages")
        while True:
            message = await loop.run_in_executor(None, self.__cursor.fetchone)
            if message is None:
                break
            yield self._get_universal_message(message)

    def __download_media(self, message: Message) -> Optional[str]:
        """Download the media of a message if exists and save it to a file

        Args:
            message (Message): The message to download

        Returns:
            str: The path of the downloaded file
        """
        if not message.media:
            return
        # TODO: implement
        ...

    async def send_message(self, message: UniversalMessage):
        tg_message = message.message
        if not tg_message:
            return
        message_media_path = self.__download_media(tg_message)
        self.__cursor.execute(
            "insert into messages (chat_id, message_id, message_text, message_media_path) values (?, ?, ?, ?)",
            (
                self.chat_id,
                tg_message.id,
                tg_message.message,
                message_media_path,
            ),
        )
        self.__conn.commit()


async def get_target(
    client: TelegramClient, target_id: Union[int, Path]
) -> Target:
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
        return await TgChat.create(client, target_id)

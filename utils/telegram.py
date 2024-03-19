import asyncio
import logging
import os
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncGenerator, Optional, Union

from telethon import TelegramClient
from telethon.tl.patched import MessageService
from telethon.tl.types import Channel, Chat, Message, User

from utils.base import create_callback, get_filename


class UniversalMessage:
    """Universal Message Representation"""

    def __init__(
        self, client: TelegramClient, chat_id: int, message_id: int, retrieve: bool = True, **kw
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
        _message = await self.client.get_messages(self.chat_id, ids=self.message_id)
        if _message:
            self.message = _message[0]


class Target(ABC):
    """Wrapper class for Target that implements some common methods for all targets."""

    def __init__(self, client: TelegramClient, target_id: Union[int, Path], **extra_configs):
        self.client = client
        self.target_id = target_id
        self.target_path = Path("chats") / str(target_id)
        self.forward_messages = extra_configs.get("forward_messages", False)
        self.reverse_messages = extra_configs.get("reverse_messages", False)
        self.db_path = (
            self.target_path / "dump.db"
            if not extra_configs.get("db_path")
            else extra_configs["db_path"]
        )
        self.__init_db()

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

    def __init_db(self):
        """Initialize the database connection

        Args:
            db_path (Path): The path of the database
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

        self._cursor = self._conn.cursor()
        self._create_initial_schema()

    @abstractmethod
    def _create_initial_schema(self):
        """Define an create the schema from the target messages controller db (if not exists)"""
        raise NotImplemented


class TgChat(Target):

    def __init__(self, client: TelegramClient, chat_id: int, chat_entity: ..., **extra_configs):
        super().__init__(client, chat_id, **extra_configs)
        self.target = chat_entity
        can_forward = getattr(self.target, "noforwards", False)
        if self.forward_messages and not can_forward:
            logging.warning(f"Can't forward messages from {self.target_id}")
        self.forward_messages = self.forward_messages and can_forward

    def _create_initial_schema(self):
        self.target_path.mkdir(parents=True, exist_ok=True)
        schema = """
        create table if not exists messages (
            id integer primary key,
            input_chat_id integer,
            input_message_id integer,
            output_chat_id integer,
            output_message_id integer,
            added_at datetime default current_timestamp
        );
        """
        self._cursor.executescript(schema)
        self._conn.commit()

    @classmethod
    async def create(cls, client: TelegramClient, chat_id: int, **extra_configs):
        """Create a new Chat Instance

        Args:
            client (TelegramClient): The client to use for the API call.
            chat_id (int): The ID of the chat to clone.
            extra_configs (dict, optional): Extra configurations setted by the user.

        Returns:
            Channel|Chat|User: The clonable chat entity.

        Raises:
            ValueError: If the entity is not a clonable chat.
        """
        chat_entity = await client.get_entity(chat_id)
        if not isinstance(chat_entity, (Channel, Chat, User)):
            raise ValueError(f"Entity {type(chat_entity)} is not clonable")
        return cls(client, chat_id, chat_entity, **extra_configs)

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
        last_sent_message_id = (
            result["input_message_id"]
            if (
                result := self._cursor.execute(
                    "select input_message_id from messages where input_chat_id = ? order by added_at desc limit 1",
                    (self.target_id,),
                ).fetchone()
            )
            else 0
        )

        async for message in self.client.iter_messages(
            self.target, reverse=self.reverse_messages, min_id=last_sent_message_id
        ):
            if isinstance(message, MessageService):
                continue
            yield self._get_universal_message(message)

    def __insert_sent_message(self, original_message: UniversalMessage, sent_message: Message):
        self._cursor.execute(
            "insert into messages (input_chat_id, input_message_id, output_chat_id, output_message_id) values (?, ?, ?, ?)",
            (
                original_message.chat_id,
                original_message.message_id,
                self.target_id,
                sent_message.id,
            ),
        )
        self._conn.commit()

    async def send_message(self, message: UniversalMessage) -> Optional[Message]:
        """Send a message to save on target.

        Args:
            message (UniversalMessage): The message to send.

        Returns:
            Message: Telegram Message Object
        """
        tg_message = message.message
        if not tg_message:
            return

        logging.debug(f"Sending message {tg_message.id} to {self.target_id}")

        if self.forward_messages:
            sent_messages = await self.client.forward_messages(
                self.target, tg_message, as_album=True
            )
            for sent_message in sent_messages:
                self.__insert_sent_message(message, sent_message)
            return

        save_path = (Path("chats") / str(self.target_id)) / str(tg_message.id)
        save_path.mkdir(parents=True, exist_ok=True)

        logging.debug(f"Save Path to save media of message {tg_message.id} is: {save_path}")

        if tg_message.media:
            logging.debug(f"Downloading media {tg_message.media}")
            custom_callback = create_callback(tg_message.media)
            await self.client.download_media(
                tg_message,
                str(save_path),
                progress_callback=custom_callback,
            )
            file_path = next(p for p in save_path.iterdir() if p.is_file())
            custom_callback = create_callback(tg_message.media, "Sending")
            with file_path.open("rb") as f:
                logging.debug(f"Sending message with media {tg_message.media}")
                sent_message = await self.client.send_file(
                    self.target,
                    f,
                    caption=tg_message.message,
                    progress_callback=custom_callback,
                )
            for file_path in save_path.iterdir():
                os.remove(file_path)
            save_path.rmdir()
        else:
            logging.debug(f"Sending {tg_message.id} from {message.chat_id} message without media")
            sent_message = await self.client.send_message(self.target, tg_message)

        self.__insert_sent_message(message, sent_message)


class DumpChat(Target):

    def __init__(
        self,
        client: TelegramClient,
        path: Path,
        represents_chat_id: Optional[int] = None,
        **extra_configs,
    ):
        super().__init__(client, path, **extra_configs)
        self.__get_chat_id(represents_chat_id)

    def __get_chat_id(self, represents_chat_id: Optional[int]):
        if represents_chat_id:
            self.chat_id = represents_chat_id
        else:
            chat_id = self._conn.execute("select value from meta where name = 'chat_id'").fetchone()
            if chat_id:
                self.chat_id = chat_id[0]
            else:
                self.chat_id = 0
        logging.debug(f"Chat ID: {self.chat_id}")
        self._conn.execute(
            "insert or replace into meta (name, value) values ('chat_id', ?)", (self.chat_id,)
        )
        self._conn.commit()

    def _create_initial_schema(self):
        logging.debug("Creating Initial Schema")
        schema = """
        create table if not exists messages (
            id integer primary key,
            chat_id integer,
            message_id integer,
            message_text text,
            message_media_path text,
            added_at datetime default current_timestamp
        );

        create table if not exists meta (
            id integer primary key,
            name text,
            value text
        );
        """
        self._cursor.executescript(schema)
        self._conn.commit()
        logging.debug("Initial Schema Created")

    def _get_universal_message(self, message: dict | Message):
        if isinstance(message, dict):
            return UniversalMessage(self.client, self.chat_id, message["message_id"])
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
        self._cursor.execute("SELECT * FROM messages")
        while True:
            message = await loop.run_in_executor(None, self._cursor.fetchone)
            if message is None:
                break
            yield self._get_universal_message(message)

    async def __download_media(self, message: Message) -> Optional[str]:
        """Download the media of a message if exists and save it to a file

        Args:
            message (Message): The message to download

        Returns:
            str: The path of the downloaded file
        """
        if not message.media:
            return
        save_path = self.target_path / str(message.id)
        save_path.mkdir(parents=True, exist_ok=True)

        save_path /= get_filename(message.media)

        if save_path.exists():
            return str(save_path)

        logging.debug(f"Save Path to save media of message {message.id} is: {save_path}")

        custom_callback = create_callback(message.media, "Downloading")

        await self.client.download_media(
            message,
            str(save_path),
            progress_callback=custom_callback,
        )

        save_path = next(p for p in save_path.iterdir() if p.is_file())
        return str(save_path)

    async def send_message(self, message: UniversalMessage):
        tg_message = message.message
        if not tg_message:
            return
        message_media_path = await self.__download_media(tg_message)
        self._cursor.execute(
            "insert into messages (chat_id, message_id, message_text, message_media_path) values (?, ?, ?, ?)",
            (
                self.chat_id,
                tg_message.id,
                tg_message.message,
                message_media_path,
            ),
        )
        self._conn.commit()


async def get_target(client: TelegramClient, target_id: Union[int, Path], **kw) -> Target:
    """Get a target object by ID

    Args:
        client (TelegramClient): The client to use for the API call.
        target_id (Union[int, Path]): The ID of the target chat.
        **kw: Additional keyword arguments.

    Returns:
        Target: The target wrapper object.
    """
    if isinstance(target_id, Path):
        logging.debug(f"Target {target_id} is a local dump")
        return DumpChat(client, target_id, **kw)
    else:
        logging.debug(f"Target {target_id} is a remote telegram chat")
        return await TgChat.create(client, target_id, **kw)

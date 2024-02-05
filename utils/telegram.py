import asyncio
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncGenerator, Optional, Union

from telethon import TelegramClient
from telethon.tl.patched import MessageService
from telethon.tl.types import (
    Channel,
    DocumentAttributeFilename,
    DocumentEmpty,
    InputDocumentFileLocation,
    InputPhotoFileLocation,
    Message,
    MessageMediaDocument,
    MessageMediaPhoto,
)

# TODO: Add Verbose on Actions (sent, iter, download, etc...)


class UniversalMedia:
    """Universal Media Representation"""

    def __init__(self, file_name: str, file_path: Optional[Path] = None, **kw):
        from utils.base import create_callback

        self.file_name = file_name
        self.file_path = file_path
        self.id = kw.get("id")
        self.access_hash = kw.get("access_hash")
        self.file_reference = kw.get("file_reference")
        self.is_photo = kw.get("is_photo", False)
        self.total_bytes = kw.get("total_bytes", None)
        self.download_callback = create_callback(self)
        if isinstance(self.file_reference, str):
            self.file_reference = self.file_reference.encode("utf-8")

    async def download_media(self, client: TelegramClient):
        """Use the client to download the media.

        Args:
            client (TelegramClient): The client to use for the API call.
        """
        if any(not v for v in (self.id, self.access_hash, self.file_reference)):
            return None

        id, access_hash, file_reference = (
            getattr(self, k) for k in ("id", "access_hash", "file_reference")
        )
        input_cls = (
            InputPhotoFileLocation
            if self.is_photo
            else InputDocumentFileLocation
        )
        input_file = input_cls(id, access_hash, file_reference, "")
        if not self.file_path:
            self.file_path = self.file_name  # TODO: change thin in the init

        await client.download_file(
            input_file,
            str(self.file_path),
            progress_callback=self.download_callback,
            file_size=self.total_bytes,
        )


class UniversalMessage:
    """Universal Message Representation"""

    def __init__(
        self, message: str = "", file: Optional[UniversalMedia] = None
    ):
        self.message = message
        self.file = file


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


class Chat(Target):

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

    async def _get_universal_media(
        self, media: "MediaMessage"  # type: ignore [abstract constructor]
    ) -> Union[UniversalMedia, None]:
        """Convert a message media to UniversalMedia

        Args:
            media (MessageMedia): The message media to convert.

        Returns:
            Union[UniversalMedia, None]: UniversalMedia if media is not empty.
        """
        data = {}
        # should i use match case? ho ho ho
        if isinstance(media, MessageMediaDocument):
            property = "document"
        elif isinstance(media, MessageMediaPhoto):
            property = "photo"
        else:
            return None

        property_value = getattr(media, property)
        if isinstance(property_value, DocumentEmpty) or not property_value:
            return None

        fname_attr = next(
            (
                attr
                for attr in getattr(property_value, "attributes", [])
                if isinstance(attr, DocumentAttributeFilename)
            ),
            None,
        )

        if not fname_attr or property == "photo":
            filename = f"{property_value.id}.jpg"
        else:
            filename = fname_attr.file_name

        if property == "document":
            file_size = property_value.size
        elif property == "photo":
            file_size = next(
                size.size
                for size in property_value.sizes
                if getattr(size, "size", None)
            )
        else:
            file_size = 1  # just for type checking

        data["file_name"] = filename
        data["id"] = property_value.id
        data["access_hash"] = property_value.access_hash
        data["file_reference"] = property_value.file_reference
        data["is_photo"] = property == "photo"
        data["total_bytes"] = file_size

        return UniversalMedia(**data)

    async def _get_universal_message(self, message: Union[dict, Message]):
        """Convert a message to UniversalMessage

        Args:
            message (Union[dict, Message]): The message to convert.

        Returns:
            UniversalMessage: The converted message.
        """
        if isinstance(message, dict):
            return UniversalMessage(**message)

        message_data = {}
        message_data["message"] = message.message
        if message.media:
            message_data["file"] = await self._get_universal_media(
                message.media
            )

        return UniversalMessage(**message_data)

    async def iter_messages(self):
        async for message in self.client.iter_messages(self.target):
            if isinstance(message, MessageService):
                continue
            yield await self._get_universal_message(message)

    async def send_message(self, message: UniversalMessage) -> Message:
        """Send a message to save on target.

        Args:
            message (UniversalMessage): The message to send.

        Returns:
            Message: Telegram Message Object
        """
        if not message.file:
            return await self.client.send_message(self.target, message.message)
        else:
            await message.file.download_media(self.client)
            return await self.client.send_file(
                self.target,
                str(message.file.file_path),
                caption=message.message,
            )


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
        # TODO: Write a SQL script to create the schema

    def _get_universal_message(self, message: dict):
        # TODO: Write the conversion (it depends of schema)
        return UniversalMessage()

    async def iter_messages(self):
        loop = asyncio.get_running_loop()
        self.__cursor.execute("SELECT * FROM messages")
        while True:
            message = await loop.run_in_executor(None, self.__cursor.fetchone)
            if message is None:
                break
            yield self._get_universal_message(message)

    async def send_message(self, message: UniversalMessage):
        return super().send_message(message)


async def get_target(
    client: TelegramClient, target_id: Union[int, Path]
) -> Union[DumpChat, Chat]:
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
        return await Chat.create(client, target_id)

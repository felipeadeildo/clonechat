import sqlite3
import time
from abc import ABC, abstractmethod
from pathlib import Path
from random import randint
from typing import AsyncGenerator, Union

from pyrogram.client import Client
from pyrogram.types import Message

from constants import MEDIA_TYPES

from .message import UniversalMessage


class Target(ABC):
    """Wrapper class for Target that implements some common methods for all targets."""

    def __init__(self, client: Client, target_id: Union[int, Path], **extra_configs):
        self.client = client
        self.target_id = target_id
        self.target_path = Path("chats") / str(target_id)
        self.forward_messages = extra_configs.get("forward_messages", False)
        self.reverse_messages = extra_configs.get("reverse_messages", False)
        self.threads = extra_configs.get("threads", 1)
        self.sleep_range = extra_configs.get("sleep_range", (0, 5))
        self.send_text_messages = extra_configs.get("send_text_messages", False)
        self.media_types = extra_configs.get("media_types", MEDIA_TYPES)
        self.db_path = (
            self.target_path / "dump.db"
            if not extra_configs.get("db_path")
            else extra_configs["db_path"]
        )

        from ..base import (
            create_callback,
            get_filename,
            get_friendly_chat_name,
            get_message_url,
        )

        self.get_friendly_chat_name = get_friendly_chat_name
        self.friendly_name = ""
        self.get_filename = get_filename
        self.get_message_url = get_message_url
        self.create_callback = create_callback
        self.__init_db()

    @abstractmethod
    async def iter_messages(self) -> AsyncGenerator[UniversalMessage, None]:
        """Async generator of messages [UniversalMessage]"""
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, message: UniversalMessage):
        """Send a message to save on target.

        Args:
            message (UniversalMessage): The message to send.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_universal_message(self, message: Union[dict, Message]):
        """Convert a message to [UniversalMessage]

        Args:
            message (Union[dict, Message]): The message to convert.
                Is a dict if from `DumpChat`, else from `Chat`.
        """
        raise NotImplementedError

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
        raise NotImplementedError

    def _random_sleep(self, multiplier: int = 1):
        time_to_sleep = randint(*self.sleep_range) * multiplier
        time_piece = 0.01
        while time_to_sleep > 0:
            print(f"\rWaiting {time_to_sleep:.2f} to continue...", end="", flush=True)
            time.sleep(time_piece)
            time_to_sleep -= time_piece
        else:
            print()

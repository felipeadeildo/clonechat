import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Union

from pyrogram.client import Client
from pyrogram.types import Chat, ChatPreview, Message

from .abstract import Target
from .message import UniversalMessage


class TgChat(Target):

    def __init__(self, client: Client, chat_id: int, chat_entity: Chat, **extra_configs):
        super().__init__(client, chat_id, **extra_configs)
        self.target = chat_entity
        self.friendly_name = self.get_friendly_chat_name(self, client)
        can_forward = not chat_entity.has_protected_content
        if self.forward_messages and not can_forward:
            logging.warning(f"Can't forward messages from {self.friendly_name}")
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
    async def create(cls, client: Client, chat_id: int, **extra_configs):
        """Create a new Chat Instance

        Args:
            client (Client): The client to use for the API call.
            chat_id (int): The ID of the chat to clone.
            extra_configs (dict, optional): Extra configurations setted by the user.

        Returns:
            TgChat: A new TgChat instance.

        Raises:
            ValueError: If the user is not a member of the chat.
        """
        chat_entity = await client.get_chat(chat_id)
        if isinstance(chat_entity, ChatPreview):
            raise ValueError("You must be a member of the chat to clone it")
        return cls(client, chat_id, chat_entity, **extra_configs)

    def _get_universal_message(self, message: dict | Message):
        chat_id = int(getattr(self, "target_id"))
        if isinstance(message, dict):
            return UniversalMessage(
                self.client, chat_id, message["id"], can_forward=self.forward_messages
            )
        else:
            return UniversalMessage(
                self.client,
                chat_id,
                message.id,
                retrieve=False,
                message=message,
                can_forward=self.forward_messages,
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

        # TODO: Apply reverse function here if needed by self.reverse_messages
        messages_generator = self.client.get_chat_history(
            self.target.id, offset_id=last_sent_message_id
        )

        async for message in messages_generator:  # type: ignore [is iterable]
            if getattr(message, "service"):
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

        logging.info(f"Sending message {self.get_message_url(tg_message)} to {self.friendly_name}")

        if message.can_forward:
            sent_messages = await self.client.copy_message(
                self.target.id, message.chat_id, tg_message.id
            )
            if isinstance(sent_messages, Message):
                self.__insert_sent_message(message, sent_messages)
            # else:
            #     for sent_message in sent_messages:
            #         self.__insert_sent_message(message, sent_message)
            return

        save_path = (Path("chats") / str(self.target_id)) / str(tg_message.id)
        save_path.mkdir(parents=True, exist_ok=True)

        logging.info(
            f"Save Path to save media of message {self.get_message_url(tg_message)} is: {save_path}"
        )

        if tg_message.media:
            media_type = tg_message.media.value
            media = getattr(tg_message, str(media_type))

            logging.info(
                f"Downloading media {self.get_filename(media)} from {self.get_message_url(tg_message)}"
            )

            custom_callback = self.create_callback(media)
            file_path = await self.client.download_media(
                tg_message,
                str(save_path) + "/",
                progress=custom_callback,
            )
            if not isinstance(file_path, str):
                return logging.error("An error ocurred when trying to download the file. Skipping.")
            file_path = Path(file_path)
            custom_callback = self.create_callback(media, "Sending")
            with file_path.open("rb") as f:

                logging.debug(f"Sending message with media {media}")

                send_function = getattr(self.client, f"send_{media_type}")
                args = [self.target.id, f]
                kwargs = {"caption": tg_message.text, "progress": custom_callback}
                if media_type not in ("photo", "audio", "sticker"):
                    kwargs["file_name"] = file_path.name

                try:
                    sent_message = await send_function(*args, **kwargs)
                except ValueError:
                    logging.warning(
                        "An error ocurred when trying to send the file, trying to send again..."
                    )
                    return await self.send_message(message)
            for file_path in save_path.iterdir():
                os.remove(file_path)
            save_path.rmdir()
        else:
            logging.info(f"Sending {self.get_message_url(tg_message)} message without media")
            sent_message = await self.client.send_message(self.target.id, tg_message.text)

        if sent_message:
            self.__insert_sent_message(message, sent_message)


class DumpChat(Target):

    def __init__(
        self,
        client: Client,
        path: Path,
        represents_chat_id: Optional[int] = None,
        **extra_configs,
    ):
        super().__init__(client, path, **extra_configs)
        self.__get_chat_id(represents_chat_id)
        self.friendly_name = self.get_friendly_chat_name(self, client)

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

        save_path /= self.get_filename(message.media)

        if save_path.exists():
            return str(save_path)

        logging.debug(
            f"Save Path to save media of message {self.get_message_url(message)} is: {save_path}"
        )

        custom_callback = self.create_callback(message.media, "Downloading")

        await self.client.download_media(
            message,
            str(save_path),
            progress=custom_callback,
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
                tg_message.text,
                message_media_path,
            ),
        )
        self._conn.commit()


async def get_target(client: Client, target_id: Union[int, Path], **kw) -> Target:
    """Get a target object by ID

    Args:
        client (Client): The client to use for the API call.
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

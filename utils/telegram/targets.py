import logging
import os
from pathlib import Path
from typing import Optional

from pyrogram.client import Client
from pyrogram.errors.exceptions.flood_420 import FloodWait
from pyrogram.types import Chat, ChatPreview, Message

from utils.client import get_client

from .abstract import Target
from .message import UniversalMessage


class TgChat(Target):
    def __init__(
        self, client: Client, chat_id: int, chat_entity: Chat, **extra_configs
    ):
        super().__init__(client, chat_id, **extra_configs)
        self.target = chat_entity
        self.friendly_name = self.get_friendly_chat_name(self)
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
    async def create(
        cls,
        client: Client,
        *,
        chat_id: Optional[int],
        chat: Optional[Chat],
        **extra_configs,
    ):
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
        if chat_id:
            chat_entity = await client.get_chat(chat_id)
            if isinstance(chat_entity, ChatPreview):
                raise ValueError("You must be a member of the chat to clone it")
        elif chat:
            chat_entity = chat
            chat_id = chat_entity.id
        else:
            raise ValueError("No chat_id or chat provided")
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

        messages_generator = self.client.get_chat_history(
            self.target.id,
            offset_id=last_sent_message_id if not self.reverse_messages else 0,
        )
        messages_iterator = []
        if self.reverse_messages:
            logging.info("Reversing messages (it may take a while)")
            async for message in messages_generator:  # type: ignore [is iterable]
                if message.id <= last_sent_message_id:
                    continue
                messages_iterator.append(message)

            for message in reversed(messages_iterator):
                if getattr(message, "service"):
                    continue
                if not self.send_text_messages and message.media is None:
                    continue
                if media := message.media:
                    media_type = str(media.value)
                    if media_type not in self.media_types:
                        continue
                yield self._get_universal_message(message)
        else:
            async for message in messages_generator:  # type: ignore [is iterable]
                if getattr(message, "service"):
                    continue
                if not self.send_text_messages and message.media is None:
                    continue
                if media := message.media:
                    media_type = str(media.value)
                    if media_type not in self.media_types:
                        continue
                yield self._get_universal_message(message)

    def __insert_sent_message(
        self, original_message: UniversalMessage, sent_message: Message
    ):
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

        friendly_sender_chat_name = self.get_friendly_chat_name(tg_message.chat)

        save_path = Path("chats") / str(self.target_id) / str(tg_message.id)
        logging.info(
            f"Sending message {self.get_message_url(tg_message)} from '{friendly_sender_chat_name}' to '{self.friendly_name}' (saved in {save_path})"
        )

        if message.can_forward:
            try:
                sent_messages = await self.client.copy_message(
                    self.target.id, message.chat_id, tg_message.id
                )
            except ValueError:
                logging.error(
                    f"The message {self.get_message_url(tg_message)} cannot be forwarded. Skipping."
                )
                return
            except FloodWait as e:
                logging.error(
                    f"The message {self.get_message_url(tg_message)} cannot be forwarded beacause of FloodWait. Error: {e}"
                )
                self._random_sleep(multiplier=15)
                await self.__restart_client()
                return await self.send_message(message)
            if isinstance(sent_messages, Message):
                self.__insert_sent_message(message, sent_messages)
            return

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
                return logging.error(
                    "An error ocurred when trying to download the file. Skipping."
                )
            file_path = Path(file_path)
            custom_callback = self.create_callback(media, "Sending")
            file_buffer = file_path.open("rb")

            logging.debug(f"Sending message with media {media}")

            send_function = getattr(self.client, f"send_{media_type}")
            args = [self.target.id, file_buffer]
            kwargs = {"caption": tg_message.text, "progress": custom_callback}
            if media_type not in ("photo", "audio", "sticker"):
                kwargs["file_name"] = file_path.name

            if media_type in ("sticker",):
                kwargs.pop("caption", None)

            try:
                sent_message = await send_function(*args, **kwargs)
                self._random_sleep()
            except ValueError as e:
                logging.error(
                    f"An error ocurred when trying to send the file (Probably API Spam): {e}"
                )
                file_buffer.close()
                self._random_sleep(multiplier=15)
                await self.__restart_client()

                return await self.send_message(message)
            else:
                file_buffer.close()
            for file_path in save_path.iterdir():
                os.remove(file_path)
            save_path.rmdir()
        else:
            logging.info(
                f"Sending {self.get_message_url(tg_message)} message without media"
            )
            sent_message = await self.client.send_message(
                self.target.id, tg_message.text
            )
            self._random_sleep()

        if sent_message:
            self.__insert_sent_message(message, sent_message)

    async def __restart_client(self):
        await self.client.disconnect()
        self.client = await get_client()


async def get_target(
    client: Client, *, chat_id: Optional[int] = None, chat: Optional[Chat] = None, **kw
) -> Target:
    """Get a target object by ID

    Args:
        client (Client): The client to use for the API call.
        target_id (int): The ID of the target chat.
        **kw: Additional keyword arguments.

    Returns:
        Target: The target wrapper object.
    """
    logging.debug(f"Target {chat_id} is a remote telegram chat")
    return await TgChat.create(client, chat_id=chat_id, chat=chat, **kw)

import asyncio
import logging
import shutil
from pathlib import Path
from typing import List

# from pyrogram.enums import ChatType
# from pyrogram.raw.functions.channels.get_forum_topics import GetForumTopics
# from pyrogram.raw.types.input_peer_channel import InputPeerChannel
from pyrogram.types import Chat, Dialog

from utils.base import get_friendly_chat_name, is_yes_answer
from utils.cli import get_args
from utils.client import get_client
from utils.telegram.targets import get_target

try:
    import uvloop
except:  # noqa: E722
    uvloop = None

from pyrogram.client import Client


class CloneChat:
    """Controller for CloneChat

    Methods:
        clone(self): Clone Target Chat to Output Chat
    """

    def __init__(
        self,
        client: Client,
        input_id: int,
        output_id: int,
        **extra_configs,
    ):
        """Initialize the controller

        Args:
            client (TelegramClient): The client to use for the API call.
            input_id (int): if `int`: The ID of the chat to clone.
                if `Path`: A dumpped chat folder containing dump.db file.
            output_id (int): if `int`: The ID of the chat to send cloned messages.
                if `Path`: A dumpped chat to dump the chat into dump.db file.
        """
        self.client = client
        self.input_id = input_id
        self.output_id = output_id
        self.extra_configs = extra_configs

    async def __get_targets(self):
        """Initialize Target and Output Chat"""
        logging.debug("Initializing Targets")
        self.input = await get_target(
            self.client, chat_id=self.input_id, **self.extra_configs
        )

        self.extra_configs.update({"represents_chat_id": self.input_id})
        self.output = await get_target(
            self.client,
            chat_id=self.output_id,
            **{**self.extra_configs, "db_path": self.input.db_path},
        )
        logging.debug("Targets Initialized")

    async def clone(self):
        """Start the clonation process"""
        await self.__get_targets()
        logging.info(
            f"Cloning from {self.input.friendly_name} to {self.output.friendly_name}"
        )
        await self.__clone_messages()

    async def __clone_messages(self):
        """Iterate over messages and call the wrapper clonator method."""
        logging.debug(f"Walking over messages of {self.input.friendly_name}")
        async for message in self.input.iter_messages():  # type: ignore
            await self.output.send_message(message)


class InteractiveCloneChat:
    def __init__(self, client: Client):
        self.client = client

    async def __get_target_chat(self, dialogs: List[Dialog]) -> Chat:
        choice = input("Do you want set the chat_id manually? [y/N] ")
        if is_yes_answer(choice):
            chat_id = int(input("Enter the chat_id: "))
            chat = await self.client.get_chat(chat_id)
            if not isinstance(chat, Chat):
                print("Invalid Chat ID or you need be a member of the chat to clone it")
                print("Try again.")
                return await self.__get_target_chat(dialogs)
            return chat

        for i, dialog in enumerate(dialogs):
            print(f"{i+1}. {get_friendly_chat_name(dialog)}")
        choice = int(input("Choose one of the above: "))
        return dialogs[choice - 1].chat

    async def __get_target_chats(self) -> tuple[Chat, Chat]:
        dialogs = []
        print("Loading dialogs...", end=" ")
        async for dialog in self.client.get_dialogs():  # type: ignore
            dialogs.append(dialog)
        print("Done!")

        print("Select the chat you want to clone: ")
        input_chat = await self.__get_target_chat(dialogs)

        print("Select the chat you want to clone to: ")
        output_chat = await self.__get_target_chat(dialogs)
        return input_chat, output_chat

    # async def __get_topic(self, chat: Chat):
    #     channel = await self.client.resolve_peer(chat.id)
    #     if not isinstance(channel, InputPeerChannel):
    #         logging.warning(f"Can't get topic from {get_friendly_chat_name(chat)}")
    #         return 0

    #     topics = GetForumTopics(
    #         channel=channel, offset_date=0, offset_id=0, offset_topic=0, limit=100  # type: ignore
    #     )

    async def run(self):
        self.input_chat, self.output_chat = await self.__get_target_chats()

        config = {
            "forward_messages": is_yes_answer(input("Try to Forward messages? [y/N] ")),
            "reverse_messages": is_yes_answer(input("Try to Reverse messages? [y/N] ")),
            "threads": int(
                input("How many simultaneous downloads do you want? [1-10] ")
            ),
        }

        self.input = await get_target(self.client, chat=self.input_chat, **config)
        self.output = await get_target(
            self.client,
            chat=self.output_chat,
            **{**config, "db_path": self.input.db_path},
        )

        # if self.input.type == ChatType.SUPERGROUP:
        #     select_topic = input(
        #         f"Do you want to select a topic from {get_friendly_chat_name(self.input)}? [y/N] "
        #     )
        #     if is_yes_answer(select_topic):
        #         topic = await self.__get_topic(self.input)

        await self.__clone_messages()

    async def __clone_messages(self):
        """Iterate over messages and call the wrapper clonator method."""
        logging.debug(f"Walking over messages of {self.input.friendly_name}")
        async for message in self.input.iter_messages():  # type: ignore
            await self.output.send_message(message)


async def main():
    args = get_args()

    logging.basicConfig(
        level=getattr(logging, args.loglevel.upper()),
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        handlers=[logging.StreamHandler()],
    )

    logging.getLogger("pyrogram").setLevel(logging.CRITICAL)

    if args.command == "clone":
        client = await get_client()

        extra_configs = {
            "forward_messages": args.forward,
            "reverse_messages": args.reverse,
        }

        input_id, output_id = args.input, args.output

        async with client:
            await CloneChat(client, input_id, output_id, **extra_configs).clone()

    elif args.command == "cleanup":
        chats_path = Path("chats")
        if chats_path.exists():
            shutil.rmtree(chats_path)
        logging.info(f"Removed {chats_path}. The directory is now empty.")

    elif args.command == "interactive":
        client = await get_client()
        async with client:
            await InteractiveCloneChat(client).run()

    else:
        logging.error(f"Invalid Command: {args.command}")


if __name__ == "__main__":
    if uvloop is not None:
        uvloop.install()
    asyncio.run(main())

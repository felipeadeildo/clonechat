import asyncio

from pyrogram.client import Client
from pyrogram.types import ChatPreview, Message


class UniversalMessage:
    """Universal Message Representation"""

    def __init__(
        self,
        client: Client,
        chat_id: int,
        message_id: int,
        retrieve: bool = True,
        can_forward: bool = True,
        **kw,
    ):
        self.client = client
        self.chat_id = chat_id
        self.message_id = message_id
        self.message: Message | None = None
        self.can_forward = can_forward
        for k, v in kw.items():
            setattr(self, k, v)
        if retrieve:
            asyncio.run(self.retrieve_message())

    async def retrieve_message(self):
        chat = await self.client.get_chat(self.chat_id)
        if isinstance(chat, ChatPreview):
            raise ValueError("You must be a member of the chat to clone it")
        self.can_forward = not chat.has_protected_content
        _message = await self.client.get_messages(chat.id, message_ids=self.message_id)
        if isinstance(_message, Message):
            self.message = _message
        else:
            self.message = _message[0]

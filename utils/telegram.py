from telethon import TelegramClient
from telethon.tl.types import Channel


# TODO: Create a abstract class for clonable inputs entities, implementing methods to copy, forward, etc.
# the ideia is: instead use `get_entity`, encapsulate the entity (chat or path) and implemente function to use by controller.
# so, the get_chat will return other type.
async def get_chat(client: TelegramClient, chat_id: int) -> Channel:
    """Get a clonable chat entity by ID.

    Args:
        client (TelegramClient): The client to use for the API call.
        chat_id (int): The ID of the chat to clone.

    Returns:
        Channel: The clonable chat entity.
    
    Raises:
        ValueError: If the entity is not a clonable chat.
    """
    entity = await client.get_entity(chat_id)
    if not isinstance(entity, (Channel, )):
        raise ValueError("Entity is not Clonable Chat")
    return entity

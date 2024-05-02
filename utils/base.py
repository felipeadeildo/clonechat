import logging
from typing import Callable, Literal, Optional

from pyrogram.enums import MessageMediaType
from pyrogram.types import Chat, Dialog, Message

from .telegram.abstract import Target
from .telegram.targets import TgChat


def get_filename(media: Optional[MessageMediaType]) -> str:
    """Get the filename of the media

    Args:
        media (UniversalMedia): The media to get the filename from

    Returns:
        str: The filename
    """
    filename = getattr(media, "file_name", None)
    media_type = getattr(media, "media_type", "jpg").split("/")[0]
    return filename or f"Unknown.{media_type}"


def create_callback(
    media: Optional[MessageMediaType],
    action: Literal["Downloading", "Sending"] = "Downloading",
) -> Callable[[int, int], None]:
    """Create a Personalized callback for media download progress

    Args:
        media (UniversalMedia): The media to construct the callback

    Returns:
        Callable[[int, int], None]: The callback
    """

    def in_mb(bytes: int) -> float:
        return bytes / 1024 / 1024

    filename = get_filename(media)

    def callback(download_bytes, total: int = 0):
        percent = download_bytes / total * 100
        finished = download_bytes == total
        text = f"{action} {filename}: ({percent:.2f}%) {in_mb(download_bytes):.2f} MB / {in_mb(total):.2f} MB"
        logging.debug(text)
        print(text, end="\r" if not finished else "\n", flush=True)

    return callback


def get_friendly_chat_name(target: Target | Chat | Dialog) -> str:
    """Get the friendly name of the chat

    Args:
        target (Target): The target to get the name from

    Returns:
        str: The friendly name
    """
    name = ""
    if isinstance(target, TgChat):
        chat = target.target
    elif isinstance(target, Chat):
        chat = target
    elif isinstance(target, Dialog):
        chat = target.chat
    else:
        return f"Chat {target}"

    if first_name := getattr(chat, "first_name", None):
        name += first_name
    if last_name := getattr(chat, "last_name", None):
        name += f" {last_name}"
    if title := getattr(chat, "title", None):
        name += f" ({title})"
    if username := getattr(chat, "username", None):
        name += f" (@{username})"

    name += f" [{getattr(chat, 'id', 'Sem ID')}]"
    while "  " in name:
        name = name.replace("  ", " ")
    return name.strip()


def get_message_url(message: Message) -> str:
    return f"https://t.me/c/{str(message.chat.id).removeprefix('-100')}/{message.id}"


def is_yes_answer(answer: str) -> bool:
    return answer.lower() in ["s", "sim", "y", "yes"]

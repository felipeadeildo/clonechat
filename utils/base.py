import logging
from typing import Callable, Literal, Optional

from pyrogram.enums import MessageMediaType


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
    in_mb = lambda bytes: bytes / 1024 / 1024
    filename = get_filename(media)

    def callback(download_bytes, total: Optional[int]):
        percent = download_bytes / total * 100
        finished = download_bytes == total
        text = f"{action} {filename}: ({percent:.2f}%) {in_mb(download_bytes):.2f} MB / {in_mb(total):.2f} MB"
        logging.debug(text)
        print(text, end="\r" if not finished else "\n", flush=True)

    return callback

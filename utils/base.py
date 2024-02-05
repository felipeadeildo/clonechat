from typing import Callable, Optional

from utils.telegram import UniversalMedia


def create_callback(media: UniversalMedia) -> Callable[[int, int], None]:
    """Create a Personalized callback for media download progress

    Args:
        media (UniversalMedia): The media to construct the callback

    Returns:
        Callable[[int, int], None]: The callback
    """
    in_mb = lambda bytes: bytes / 1024 / 1024

    def callback(download_bytes, total: Optional[int]):
        percent = download_bytes / total * 100
        finished = download_bytes == total
        print(
            f"Downloading {media.file_name}: ({percent:.2f}%) {in_mb(download_bytes):.2f} MB / {in_mb(total):.2f} MB",
            end="\r" if not finished else "\n",
            flush=True,
        )

    return callback

import argparse
from pathlib import Path
from typing import Union


def __argtype(value: str) -> Union[int, Path]:
    """Parse the command line arguments

    Args:
        value (str): Command line argument value

    Returns:
        int: If the value can be converted to int, returns the value.
            This int can be a `chat_id`.
        Path: If the value can be converted to Path, returns the value.
            This Path can be a `foldername` of a dumpped chat.
    """
    try:
        return int(value)
    except:
        return Path(value)


def get_args() -> argparse.Namespace:
    """Get the command line arguments

    Returns:
        argparse.Namespace: Command line arguments.
    """
    parser = argparse.ArgumentParser(description="Telegram Clone Chat")

    parser.add_argument(
        "--input",
        metavar="INPUT",
        type=__argtype,
        help="Target Chat ID like -100123456/@channelname or a dumpped chat folder containing dump.db file.",
        required=True,
    )
    parser.add_argument(
        "--output",
        metavar="OUTPUT",
        type=__argtype,
        help="Output Chat ID like -100123456/@channelname or a foldername to dump the chat into dump.db file.",
        required=True,
    )
    parser.add_argument(
        "--loglevel",
        metavar="LOGLEVEL",
        type=str,
        default="INFO",
        help="Set the log level. Default: INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )

    args = parser.parse_args()

    return args

import argparse
from typing import Union

from constants import MEDIA_TYPES


def __argtype(value: str) -> Union[int, str]:
    """Parse the command line arguments

    Args:
        value (str): Command line argument value

    Returns:
        int: If the value can be converted to int, returns the value.
            This int can be a `chat_id`
    """
    try:
        return int(value)
    except ValueError:
        return value


def get_args() -> argparse.Namespace:
    """Get the command line arguments

    Returns:
        argparse.Namespace: Command line arguments.
    """
    parser = argparse.ArgumentParser(description="Telegram Clone Chat")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Clone Chat Command
    clone_parser = subparsers.add_parser("clone", help="Clone Chat")
    clone_parser.add_argument(
        "--input",
        "-i",
        metavar="INPUT",
        type=__argtype,
        help="Target Chat ID like -100123456/@channelname",
        required=True,
    )
    clone_parser.add_argument(
        "--output",
        "-o",
        metavar="OUTPUT",
        type=__argtype,
        help="Output Chat ID like -100123456/@channelname",
        required=True,
    )

    clone_parser.add_argument(
        "--forward",
        "-fwd",
        action="store_true",
        help="Forward the messages from input to outptut if the user is allowed to do. Default: False",
    )

    clone_parser.add_argument(
        "--reverse",
        "-rev",
        action="store_true",
        help="Reverse the message order. Default: False",
    )

    clone_parser.add_argument(
        "--threads",
        "-t",
        metavar="THREADS",
        type=int,
        default=1,
        help="Number of threads to use. Default: 1",
    )

    clone_parser.add_argument(
        "--sleep-range",
        "-sr",
        metavar="SLEEP_RANGE",
        type=int,
        nargs=2,
        default=(0, 1),
        help="Range of sleep time in seconds. Default: (0, 1)\nHow to use it: -sr 5 10 means sleep between 5 and 10 seconds",
    )

    clone_parser.add_argument(
        "--send-text-messages",
        "-stm",
        action="store_true",
        default=False,
        help="Allow the bot send text messages (message with no media). Default: False",
    )

    clone_parser.add_argument(
        "--media-types",
        "-mt",
        metavar="MEDIA_TYPE",
        type=str,
        nargs="+",
        default=MEDIA_TYPES,
        help=f"Media types that the bot is allowed to send. Default: {', '.join(MEDIA_TYPES)}",
    )

    # CleanUP Command
    subparsers.add_parser("cleanup", help="Cleanup Chats")

    # General Arguments
    parser.add_argument(
        "--loglevel",
        "-ll",
        metavar="LOGLEVEL",
        type=str,
        default="INFO",
        help="Set the log level. Default: INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.set_defaults(command="interactive")

    args = parser.parse_args()

    return args

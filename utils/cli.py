import argparse
from typing import Union


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

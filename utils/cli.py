import argparse


def get_args() -> argparse.Namespace:
    """Get the command line arguments

    Returns:
        argparse.Namespace: Command line arguments.
    """
    parser = argparse.ArgumentParser(description="Telegram Clone Chat")

    parser.add_argument('-i',
                        metavar="TARGET_CHAT_ID",
                        type=int,
                        help="Target Chat ID like -100123456",
                        required=True)
    parser.add_argument('-o',
                        metavar="OUTPUT_CHAT_ID",
                        type=int,
                        help="Output Chat ID like -100123456",
                        required=True)

    args = parser.parse_args()

    return args

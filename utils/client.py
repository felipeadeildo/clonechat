import logging
from pathlib import Path
from tomllib import load
from typing import Any

from pyrogram.client import Client

SETTINGS_FILE = Path("settings.toml")

if not SETTINGS_FILE.exists():
    _config = {
        "api_id": input("Enter API ID: "),
        "api_hash": input("Enter API Hash: "),
    }
    with open(SETTINGS_FILE, "w") as f:
        f.write("[telegram]\n")
        f.write("\n".join([f'{k} = "{v}"' for k, v in _config.items()]))


def load_settings() -> dict[str, Any]:
    """Load the configuration file in toml format"""
    with open(SETTINGS_FILE, "rb") as f:
        return load(f)


async def get_client(session_name: str = "tg_session", session_path: Path = Path(".")) -> Client:
    """Get the logged Telegram Client

    Args:
        session_name (str, optional): Session Name (session filename). Defaults to 'tg_session'.
        session_path (Path, optional): Session Path. Defaults to Path('.').

    Returns:
        Client: Telegram Client Logged Session.
    """
    logging.debug("Getting Telegram Client")
    settings = load_settings()
    telegram_settings = settings["telegram"]

    client = Client(str(session_path / session_name), **telegram_settings)

    await client.start()

    logging.debug("Telegram Client Got")

    return client

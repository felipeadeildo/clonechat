from pathlib import Path
from tomllib import load
from typing import Any

from telethon import TelegramClient

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


async def get_client(
    session_name: str = "tg_session", session_path: Path = Path(".")
) -> TelegramClient:
    """Get the logged Telegram Client

    Args:
        session_name (str, optional): Session Name (session filename). Defaults to 'tg_session'.
        session_path (Path, optional): Session Path. Defaults to Path('.').

    Returns:
        TelegramClient: Telegram Client Logged Session.
    """
    settings = load_settings()
    telegram_settings = settings["telegram"]

    client = TelegramClient(
        str(session_path / session_name), **telegram_settings
    )

    await client.connect()

    if not await client.is_user_authorized():
        phone = input("Enter phone [+5577123456789]: ")
        await client.send_code_request(phone)
        code = input("Enter code: ")
        await client.sign_in(phone, code)

    await client.start()  # type: ignore [call-start is awaitable]

    return client

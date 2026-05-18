import sys
import tomllib
from pathlib import Path
from typing import Optional


def load_credentials(config_file: Optional[str] = None) -> tuple:
    """
    Load Gmail credentials from a TOML config file.

    Searches in multiple locations (checked in order):
    - Current directory: ./gmail_sender_config.toml
    - Home directory: ~/gmail_sender_config.toml
    - Windows: ~/AppData/Local/gmail_sender_config.toml
    - Unix: ~/.config/gmail_sender_config.toml

    Args:
        config_file: Optional explicit config file path

    Returns:
        (sender_email, app_password)

    Raises:
        FileNotFoundError: if no config found
        KeyError: if required keys missing
    """
    if config_file is None:
        home = Path.home()
        cwd = Path.cwd()
        search_paths = [
            cwd / "gmail_sender_config.toml",
            home / "gmail_sender_config.toml",
        ]

        if sys.platform == "win32":
            search_paths.append(home / "AppData" / "Local" / "gmail_sender_config.toml")
        else:
            search_paths.append(home / ".config" / "gmail_sender_config.toml")

        config_file = None
        for p in search_paths:
            if p.exists():
                config_file = str(p)
                break

        if config_file is None:
            paths_str = "\n  ".join(str(p) for p in search_paths)
            raise FileNotFoundError(
                f"Config file not found in any of these locations:\n  {paths_str}\n"
                f"Create a TOML file with:\n[gmail]\n"
                f'sender_email = "your.email@gmail.com"\n'
                f'app_password = "xxxx xxxx xxxx xxxx"'
            )

    with open(config_file, "rb") as f:
        config = tomllib.load(f)

    gmail = config.get("gmail", {})
    sender = gmail.get("sender_email")
    password = gmail.get("app_password")

    if not sender or not password:
        raise KeyError("Config file must contain [gmail] section with 'sender_email' and 'app_password'")

    return sender, password

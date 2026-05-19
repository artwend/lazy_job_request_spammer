import sys
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_CONFIG_NAME = "followup_sender_config.toml"


# ---------------------------------------------------------------------------
# 1. Locating
# ---------------------------------------------------------------------------

def _default_search_paths() -> List[Path]:
    home = Path.home()
    cwd = Path.cwd()
    paths = [
        cwd / DEFAULT_CONFIG_NAME,
        home / DEFAULT_CONFIG_NAME,
    ]
    if sys.platform == "win32":
        paths.append(home / "AppData" / "Local" / DEFAULT_CONFIG_NAME)
    else:
        paths.append(home / ".config" / DEFAULT_CONFIG_NAME)
    return paths


def find_config_file(config_file: Optional[str] = None) -> Path:
    """
    Locate the config file and return its Path.

    If *config_file* is given, that path is used directly (raises
    FileNotFoundError if it does not exist).  Otherwise the standard
    search locations are tried in order.

    Raises:
        FileNotFoundError: if the file cannot be found.
    """
    if config_file is not None:
        p = Path(config_file)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {p}")
        return p

    for p in _default_search_paths():
        if p.exists():
            return p

    paths_str = "\n  ".join(str(p) for p in _default_search_paths())
    raise FileNotFoundError(
        f"Config file not found in any of these locations:\n  {paths_str}\n"
        f"Create a TOML file with:\n[gmail]\n"
        f'sender_email = "your.email@gmail.com"\n'
        f'app_password = "xxxx xxxx xxxx xxxx"'
    )


# ---------------------------------------------------------------------------
# 2. Reading (deserialise TOML → dict)
# ---------------------------------------------------------------------------

def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Locate and read the TOML config file, returning the raw dict.

    Args:
        config_file: Optional explicit path; auto-discovered if None.

    Raises:
        FileNotFoundError: if no config can be found.
    """
    path = find_config_file(config_file)
    with open(path, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# 3. Verifying & extracting typed values
# ---------------------------------------------------------------------------

def verify_config(config: Dict[str, Any]) -> None:
    """
    Verify that the loaded config dict contains all required fields.

    Raises:
        KeyError: if [gmail] sender_email or app_password are missing.
    """
    gmail = config.get("gmail", {})
    if not gmail.get("sender_email") or not gmail.get("app_password"):
        raise KeyError(
            "Config file must contain [gmail] section with 'sender_email' and 'app_password'"
        )


def read_credentials(config: Dict[str, Any]) -> Tuple[str, str]:
    """
    Extract Gmail credentials from an already-loaded config dict.

    Returns:
        (sender_email, app_password)

    Raises:
        KeyError: if required keys are missing (via verify_config).
    """
    verify_config(config)
    gmail = config["gmail"]
    return gmail["sender_email"], gmail["app_password"]


def read_exceptions(config: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
    """
    Extract skip rules from the [exceptions] section of a loaded config dict.

    Returns:
        (skip_status, skip_companies)
            skip_status    – status value that should be skipped (e.g. "absage"),
                             or None if not configured
            skip_companies – list of company names to skip (may be empty);
                             supports both a single string and a TOML array
    """
    exc = config.get("exceptions", {})
    skip_status = exc.get("status") or None
    raw_companies = exc.get("company", "")
    if isinstance(raw_companies, list):
        skip_companies = [c.strip() for c in raw_companies if c.strip()]
    else:
        skip_companies = [raw_companies.strip()] if raw_companies.strip() else []
    return skip_status, skip_companies


# ---------------------------------------------------------------------------
# Convenience wrappers (load + verify + read in one call)
# ---------------------------------------------------------------------------

def load_credentials(config_file: Optional[str] = None) -> Tuple[str, str]:
    """Load the config file and return (sender_email, app_password)."""
    return read_credentials(load_config(config_file))


def load_exceptions(config_file: Optional[str] = None) -> Tuple[Optional[str], List[str]]:
    """Load the config file and return (skip_status, skip_companies)."""
    try:
        return read_exceptions(load_config(config_file))
    except FileNotFoundError:
        return None, []

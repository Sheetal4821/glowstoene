"""Simple password authentication for the admin panel."""

import bcrypt
from pathlib import Path
from . import config


def get_stored_hash() -> bytes | None:
    """Read the stored password hash, or None if not set."""
    if config.PASSWORD_HASH_FILE.is_file():
        return config.PASSWORD_HASH_FILE.read_bytes().strip()
    return None


def set_password(password: str) -> None:
    """Hash and store a new admin password."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    config.PASSWORD_HASH_FILE.write_bytes(hashed)


def check_password(password: str) -> bool:
    """Verify a password against the stored hash."""
    stored = get_stored_hash()
    if stored is None:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), stored)


def password_is_set() -> bool:
    """Check if a password has been configured."""
    return get_stored_hash() is not None

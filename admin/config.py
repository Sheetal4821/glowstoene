"""Admin panel configuration."""

import os
import secrets
from pathlib import Path

# Paths
ADMIN_DIR = Path(__file__).resolve().parent
ROOT_DIR = ADMIN_DIR.parent
DATA_DIR = ADMIN_DIR / "data"
CATALOG_PATH = DATA_DIR / "catalog.json"
IMAGES_DIR = ROOT_DIR / "images" / "collections"

# Auth
PASSWORD_HASH_FILE = DATA_DIR / "password_hash.txt"
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
SESSION_LIFETIME_HOURS = 24

# Upload limits
MAX_UPLOAD_SIZE_MB = 20
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

"""Restore any optimized image that ended up larger than its backup original."""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "images" / "collections"
BACKUP_DIR = Path("/tmp/glowstone-image-backup")

restored = 0
total_recovered = 0

for backup in BACKUP_DIR.rglob("*"):
    if not backup.is_file():
        continue
    rel = backup.relative_to(BACKUP_DIR)
    current = IMAGES_DIR / rel
    if not current.is_file():
        continue
    cur_size = current.stat().st_size
    bak_size = backup.stat().st_size
    if cur_size > bak_size:
        shutil.copy2(backup, current)
        diff = cur_size - bak_size
        total_recovered += diff
        restored += 1
        print(f"Restored {rel}: {cur_size/1024:.0f} KB -> {bak_size/1024:.0f} KB")

print(f"\nRestored {restored} files, recovered {total_recovered/1024/1024:.1f} MB")

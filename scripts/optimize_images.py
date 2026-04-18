"""Optimize all collection images in place: resize + recompress.

- Images wider than MAX_WIDTH are resized (aspect ratio preserved).
- JPEGs are re-encoded at QUALITY.
- PNGs are optimized (lossless) and converted to palette mode when photographic
  content is not detected; otherwise kept as RGB PNG with optimize=True.
- Originals are backed up to BACKUP_DIR before being overwritten.
- Filenames and extensions are preserved (no HTML or catalog.json changes needed).

Run from project root:
    python3 scripts/optimize_images.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

# Allow very large source images (product photos can be high-res from DSLRs)
Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "images" / "collections"
BACKUP_DIR = Path("/tmp/glowstone-image-backup")

MAX_WIDTH = 1920          # max pixel width for product photos
JPEG_QUALITY = 92         # visually indistinguishable from original (high safety margin)
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def human(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def optimize_image(path: Path) -> tuple[int, int]:
    """Optimize one image in place. Returns (original_bytes, new_bytes)."""
    original_bytes = path.stat().st_size

    with Image.open(path) as img:
        img.load()
        fmt = (img.format or "").upper()
        orig_mode = img.mode

        # Resize if wider than max width
        if img.width > MAX_WIDTH:
            new_height = round(img.height * MAX_WIDTH / img.width)
            img = img.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)

        ext = path.suffix.lower()

        if ext in (".jpg", ".jpeg"):
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(
                path,
                format="JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
                progressive=True,
            )
        elif ext == ".png":
            # Preserve alpha if present
            if "A" in orig_mode or img.mode == "P":
                img.save(path, format="PNG", optimize=True)
            else:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(path, format="PNG", optimize=True)
        elif ext == ".webp":
            img.save(path, format="WEBP", quality=JPEG_QUALITY, method=6)

    return original_bytes, path.stat().st_size


def main() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    files = [p for p in IMAGES_DIR.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS]
    print(f"Found {len(files)} images in {IMAGES_DIR}")
    print(f"Backing up originals to {BACKUP_DIR}\n")

    total_before = 0
    total_after = 0
    errors: list[tuple[Path, str]] = []

    for i, path in enumerate(files, 1):
        rel = path.relative_to(IMAGES_DIR)
        backup_path = BACKUP_DIR / rel
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        if not backup_path.exists():
            shutil.copy2(path, backup_path)

        try:
            before, after = optimize_image(path)
            total_before += before
            total_after += after
            pct = (1 - after / before) * 100 if before else 0
            print(f"[{i:3d}/{len(files)}] {rel}: {human(before)} -> {human(after)} ({pct:+.0f}%)")
        except Exception as exc:
            errors.append((path, str(exc)))
            print(f"[{i:3d}/{len(files)}] ERROR {rel}: {exc}")

    print("\n" + "=" * 60)
    print(f"Total before: {human(total_before)}")
    print(f"Total after:  {human(total_after)}")
    if total_before:
        saved = total_before - total_after
        pct = saved / total_before * 100
        print(f"Saved:        {human(saved)} ({pct:.0f}%)")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for path, msg in errors:
            print(f"  {path}: {msg}")
    print(f"\nOriginals preserved in {BACKUP_DIR}")


if __name__ == "__main__":
    main()

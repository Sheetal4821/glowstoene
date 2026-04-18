"""Convert photographic PNGs (no transparency) to high-quality JPGs.

Only touches images/collections/**. Updates all references in catalog.json
and every HTML file to point at the new .jpg filenames. Originals already
backed up by optimize_images.py in /tmp/glowstone-image-backup.

JPG quality 92 is visually identical to PNG for photographic content.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "images" / "collections"
CATALOG_PATH = ROOT / "admin" / "data" / "catalog.json"
JPEG_QUALITY = 92


def has_transparency(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA") or "transparency" in img.info


def convert_pngs() -> list[tuple[Path, Path]]:
    """Convert PNGs to JPGs. Returns list of (old_path, new_path)."""
    converted = []
    for png in IMAGES_DIR.rglob("*.png"):
        with Image.open(png) as img:
            if has_transparency(img):
                continue
            rgb = img.convert("RGB")
            jpg = png.with_suffix(".jpg")
            # If a .jpg with same base already exists, skip to avoid collision
            if jpg.exists():
                print(f"Skipping {png.relative_to(IMAGES_DIR)} — {jpg.name} already exists")
                continue
            rgb.save(jpg, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        png.unlink()
        converted.append((png, jpg))
        rel = png.relative_to(IMAGES_DIR)
        old_kb = (IMAGES_DIR.parent.parent / "_stub").stat().st_size if False else 0  # noqa
        new_kb = jpg.stat().st_size / 1024
        print(f"Converted {rel} -> {jpg.name} ({new_kb:.0f} KB)")
    return converted


def update_text_references(converted: list[tuple[Path, Path]]) -> None:
    """Replace old .png filenames with new .jpg filenames in HTML and JSON."""
    targets = list(ROOT.glob("*.html")) + [CATALOG_PATH]
    # Build unique filename map (handles both short form "render.png" and full path forms)
    replacements: dict[str, str] = {}
    for old, new in converted:
        rel_from_site = old.relative_to(ROOT).as_posix()  # e.g. images/collections/.../render.png
        replacements[rel_from_site] = new.relative_to(ROOT).as_posix()
        # Also filename-only, used by catalog.json arrays
        if old.name not in replacements:
            replacements[old.name] = new.name

    for f in targets:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        original = text
        for old_str, new_str in replacements.items():
            text = text.replace(old_str, new_str)
        if text != original:
            f.write_text(text, encoding="utf-8")
            print(f"Updated references in {f.name}")


def main() -> None:
    converted = convert_pngs()
    print(f"\nConverted {len(converted)} PNG files to JPG")
    if converted:
        update_text_references(converted)
    print("Done.")


if __name__ == "__main__":
    main()

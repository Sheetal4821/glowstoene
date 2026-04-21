"""
Process slab images from Google Drive download and replace existing slab images.

Run on your Mac:
    cd ~/Desktop/glowstoene
    pip install Pillow
    python3 scripts/process_slabs.py

This script:
1. Scans ~/Desktop/slab-images-raw/ for slab images (skips Render folders)
2. Crops, resizes (max 1920px), and compresses (JPEG quality 92)
3. Replaces existing slab images in images/collections/<series>/<product>/
4. Updates catalog.json with new slab image filenames
"""

import json
import re
import shutil
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

RAW_DIR = Path.home() / "Desktop" / "slab-images-raw"
PROJECT_DIR = Path(__file__).resolve().parents[1]
COLLECTIONS_DIR = PROJECT_DIR / "images" / "collections"
CATALOG_PATH = PROJECT_DIR / "admin" / "data" / "catalog.json"

MAX_WIDTH = 1920
JPEG_QUALITY = 92

SERIES_MAP = {
    "Budget": "budget",
    "Calacatta": "calacatta",
    "carrara": "carrara",
    "Onyx": "onyx",
    "Pastel": "pastel",
    "Plain": "plain",
}

PRODUCT_MAP = {
    "Black Starlight": "black-starlight",
    "Brown starlight": "brown-starlight",
    "Brown Starlight": "brown-starlight",
    "Cream Mirror": "cream-mirror",
    "Crema": "crema",
    "Gracio": "gracio",
    "Grey Starlight": "grey-starlight",
    "Grey Terrazzo": "grey-terrazo",
    "Halo": "halo",
    "Snowflake": "snowflake",
    "Walnut": "walnut",
    "White Starlight": "white-starlight",
    "White Terrazzo": "white-terrazo",
    "Alabama": "alabama",
    "Aspen Gold": "aspen-gold",
    "Aurika": "aurika",
    "Avalanche": "avalanche",
    "Everest Grey": "everest-grey",
    "Harmony Gold": "harmony-gold",
    "Marquina Noir": "marquina-noir",
    "Narnia Gold": "narina-gold",
    "Narnia Grey": "narina-grey",
    "Nova": "nova",
    "Panda White": "panda-white",
    "Perla Venata": "perla-venata",
    "Sahara Noir": "sahara-noir",
    "Vienna": "vienna",
    "Astral": "astral",
    "Aurum": "aurum",
    "Bellagio": "bellagio",
    "Bianco Nova": "bianco-nova",
    "Blaze": "blaze",
    "Fossil": "fossil",
    "Gold Mine": "gold-mine",
    "Orion White": "orion-white",
    "Rayon": "rayon",
    "Crystal Ash": "crystal-ash",
    "Luminous Gold": "luminous-gold",
    "Marigold": "marigold",
    "Nectar": "nectar",
    "Trinity": "trinity",
    "Mauve": "mauve",
    "Peony": "peony",
    "Sage": "sage",
    "Seafoam": "seafoam",
    "Frost White": "frost-white",
    "Glacier White": "glacier-white",
    "Meraki": "meraki",
}


def is_slab_image(path: Path) -> bool:
    """Check if file is a slab image (not a render)."""
    parts = [p.lower().strip() for p in path.parts]
    if any("render" in p for p in parts):
        return False
    ext = path.suffix.lower()
    return ext in (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")


def optimize_and_save(src: Path, dest: Path) -> None:
    """Resize and compress image to high-quality JPEG."""
    with Image.open(src) as img:
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")
        if img.width > MAX_WIDTH:
            new_h = round(img.height * MAX_WIDTH / img.width)
            img = img.resize((MAX_WIDTH, new_h), Image.Resampling.LANCZOS)
        img.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)


def main():
    if not RAW_DIR.exists():
        print(f"Error: {RAW_DIR} not found")
        return

    catalog = json.loads(CATALOG_PATH.read_text())
    total_processed = 0
    total_skipped = 0

    for series_folder in sorted(RAW_DIR.iterdir()):
        if not series_folder.is_dir():
            continue
        series_key = SERIES_MAP.get(series_folder.name)
        if not series_key:
            print(f"WARNING: Unknown series folder '{series_folder.name}' — skipping")
            continue

        print(f"\n=== {series_folder.name} ({series_key}) ===")

        for product_folder in sorted(series_folder.iterdir()):
            if not product_folder.is_dir():
                continue
            slug = PRODUCT_MAP.get(product_folder.name)
            if not slug:
                print(f"  WARNING: Unknown product '{product_folder.name}' — skipping")
                continue

            # Find slab images
            slab_files = []
            for f in sorted(product_folder.rglob("*")):
                if f.is_file() and is_slab_image(f):
                    slab_files.append(f)

            if not slab_files:
                print(f"  {product_folder.name}: no slab images found")
                total_skipped += 1
                continue

            # Target directory
            dest_dir = COLLECTIONS_DIR / f"{series_key}-series" / slug
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Remove old slab images
            for old in dest_dir.glob("slab*.jpg"):
                old.unlink()

            # Process and save new slab images
            new_slab_names = []
            for i, src in enumerate(slab_files):
                if i == 0:
                    name = "slab.jpg"
                else:
                    name = f"slab-{i + 1}.jpg"
                dest = dest_dir / name
                try:
                    optimize_and_save(src, dest)
                    new_kb = dest.stat().st_size / 1024
                    new_slab_names.append(name)
                    print(f"  {slug}/{name} <- {src.name} ({new_kb:.0f} KB)")
                except Exception as e:
                    print(f"  ERROR {slug}/{name}: {e}")

            # Update catalog
            if series_key in catalog.get("series", {}):
                products = catalog["series"][series_key].get("products", {})
                if slug in products:
                    products[slug]["slab_images"] = new_slab_names
            total_processed += len(new_slab_names)

    # Save catalog
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    print(f"\n{'=' * 50}")
    print(f"Processed: {total_processed} slab images")
    print(f"Skipped: {total_skipped} products (no slab images)")
    print(f"Catalog updated: {CATALOG_PATH}")
    print(f"\nNext steps:")
    print(f"  1. Check the images look correct")
    print(f"  2. git add -A && git commit -m 'Replace slab images' && git push origin claude/review-codebase-GzWhg")


if __name__ == "__main__":
    main()

"""Add backlit slab images for Luminous Gold and Nectar (if found)."""

import json
import sys
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

COLLECTIONS_DIR = PROJECT_DIR / "images" / "collections"
CATALOG_PATH = PROJECT_DIR / "admin" / "data" / "catalog.json"

MAX_WIDTH = 1920
JPEG_QUALITY = 92

# Sources to add as new slab images
SOURCES = {
    "luminous-gold": Path.home() / "Desktop" / "glowstoene" / "files" / "serises" / "onyx series" / "slab images" / "luminous gold" / "Luminous Gold Backlit.jpg",
    "nectar": Path.home() / "Desktop" / "glowstoene" / "files" / "serises" / "onyx series" / "slab images" / "nectar" / "crystal jade backlight.jpeg",
}


def optimize_and_save(src: Path, dest: Path) -> None:
    with Image.open(src) as img:
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")
        if img.width > MAX_WIDTH:
            new_h = round(img.height * MAX_WIDTH / img.width)
            img = img.resize((MAX_WIDTH, new_h), Image.Resampling.LANCZOS)
        img.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)


def next_slab_name(product_dir: Path) -> str:
    existing = sorted(product_dir.glob("slab*.jpg"))
    if not existing:
        return "slab.jpg"
    # Find highest number
    max_num = 1
    for f in existing:
        stem = f.stem
        if stem == "slab":
            continue
        try:
            num = int(stem.split("-")[-1])
            max_num = max(max_num, num)
        except ValueError:
            pass
    return f"slab-{max_num + 1}.jpg"


def main():
    catalog = json.loads(CATALOG_PATH.read_text())
    added = 0

    for slug, src in SOURCES.items():
        if not src.is_file():
            print(f"SKIP {slug}: source not found at {src}")
            continue

        product_dir = COLLECTIONS_DIR / "onyx-series" / slug
        new_name = next_slab_name(product_dir)
        dest = product_dir / new_name

        optimize_and_save(src, dest)
        print(f"Added onyx/{slug}/{new_name} <- {src.name} ({dest.stat().st_size / 1024:.0f} KB)")

        # Update catalog
        products = catalog["series"]["onyx"]["products"]
        if slug in products:
            if new_name not in products[slug].get("slab_images", []):
                products[slug]["slab_images"].append(new_name)
                added += 1

    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    # Regenerate HTML pages
    from admin.app import SITE_ROOT
    from admin.generators.product_page import render_product_page
    from admin.generators.series_page import render_series_page
    from admin.generators.domestic_page import render_domestic_page

    for sk, series in catalog["series"].items():
        html = render_series_page(sk, series)
        (SITE_ROOT / f"collection-domestic-{sk}.html").write_text(html, encoding="utf-8")
        for slug, product in series["products"].items():
            html = render_product_page(sk, series["name"], product)
            (SITE_ROOT / f"collection-domestic-{sk}-{slug}.html").write_text(html, encoding="utf-8")
    html = render_domestic_page(catalog)
    (SITE_ROOT / "collection-domestic.html").write_text(html, encoding="utf-8")

    print(f"\nAdded {added} backlit slab images, regenerated all HTML pages")


if __name__ == "__main__":
    main()

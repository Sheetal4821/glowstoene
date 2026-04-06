"""One-time script to build catalog.json from existing HTML pages and image directories."""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parent / "data"

# Series definitions: key -> (display name, HTML filename pattern for series page)
SERIES_DEFS = {
    "onyx": "Onyx Series",
    "pastel": "Pastel Series",
    "plain": "Plain Series",
    "calacatta": "Calacatta Series",
    "budget": "Budget Series",
    "carrara": "Carrara Series",
}

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def find_series_products(series_key):
    """Find all product HTML files for a given series."""
    pattern = f"collection-domestic-{series_key}-*.html"
    return sorted(ROOT.glob(pattern))


def extract_product_data(html_path, series_key):
    """Extract product data from a product HTML page."""
    text = html_path.read_text(encoding="utf-8")

    # Product name from <h1>
    m = re.search(r"<h1>(.+?)</h1>", text)
    name = m.group(1).strip() if m else ""

    # Description
    m = re.search(r'<dd class="product-description">\s*<p>(.+?)</p>', text, re.DOTALL)
    description = m.group(1).strip() if m else (
        "Premium engineered quartz for kitchens, vanities, and commercial use\u2014"
        "durable, low-maintenance, and consistent in colour."
    )

    # Thickness
    m = re.search(r"<dt>Thickness</dt>\s*<dd>(.+?)</dd>", text, re.DOTALL)
    thickness = m.group(1).strip() if m else (
        "20 mm &amp; 30 mm (availability may vary by design \u2014 confirm with Glowstone)."
    )
    # Decode HTML entities for storage
    thickness = thickness.replace("&amp;", "&")

    # Size
    m = re.search(r"<dt>Size</dt>\s*<dd>(.+?)</dd>", text, re.DOTALL)
    size_raw = m.group(1).strip() if m else ""
    # Clean HTML tags for storage
    size = re.sub(r"<[^>]+>", "", size_raw).strip()
    if not size:
        size = "Jumbo 323 \u00d7 163 cm \u00b7 Super Jumbo 350 \u00d7 200 cm (nominal slab formats)."

    # Derive slug from filename
    fname = html_path.stem  # e.g. collection-domestic-calacatta-alabama
    prefix = f"collection-domestic-{series_key}-"
    slug = fname[len(prefix):]

    # Find images from the filesystem
    img_dir = ROOT / "images" / "collections" / f"{series_key}-series" / slug
    slab_images = []
    render_images = []
    if img_dir.is_dir():
        for f in sorted(img_dir.iterdir()):
            if f.suffix.lower() not in IMG_EXT:
                continue
            if f.stem.startswith("slab"):
                slab_images.append(f.name)
            elif f.stem.startswith("render"):
                render_images.append(f.name)

    # Sort slabs: slab.jpg first, then slab-2.jpg, slab-3.jpg, etc.
    def slab_sort(n):
        if n.split(".")[0] == "slab":
            return (0, 0)
        m2 = re.match(r"slab-(\d+)", n)
        return (1, int(m2.group(1))) if m2 else (2, 0)

    slab_images.sort(key=slab_sort)

    # Sort renders: render.png first, then render-1.png, etc.
    def render_sort(n):
        stem = n.rsplit(".", 1)[0]
        if stem == "render":
            return (0, 0)
        m2 = re.match(r"render-(\d+)", stem)
        return (1, int(m2.group(1))) if m2 else (2, 0)

    render_images.sort(key=render_sort)

    return {
        "name": name,
        "slug": slug,
        "description": description,
        "thickness": thickness,
        "size": size,
        "slab_images": slab_images,
        "render_images": render_images,
    }


def extract_series_data(series_key, series_name):
    """Extract series-level data from the series listing page."""
    series_html = ROOT / f"collection-domestic-{series_key}.html"
    description = ""
    hero_image = ""
    card_image = ""

    if series_html.is_file():
        text = series_html.read_text(encoding="utf-8")

        # Series description from .series-intro
        m = re.search(r'<div class="series-intro[^"]*"[^>]*>\s*<p>(.+?)</p>', text, re.DOTALL)
        if m:
            description = m.group(1).strip()

        # Hero image
        m = re.search(r'background-image:\s*url\([\'"]?([^\'")]+)', text)
        if m:
            hero_image = m.group(1)

    # Card image from domestic collection page (first render of first product)
    domestic_html = ROOT / "collection-domestic.html"
    if domestic_html.is_file():
        text = domestic_html.read_text(encoding="utf-8")
        pattern = (
            rf'href="collection-domestic-{series_key}\.html"[^>]*>\s*'
            rf'<img\s+src="([^"]+)"'
        )
        m = re.search(pattern, text, re.DOTALL)
        if m:
            card_image = m.group(1)

    return {
        "name": series_name,
        "description": description,
        "hero_image": hero_image,
        "card_image": card_image,
    }


def build_catalog():
    """Build the full catalog from existing HTML and image files."""
    catalog = {"series": {}}

    order = 1
    for series_key, series_name in SERIES_DEFS.items():
        series_data = extract_series_data(series_key, series_name)
        series_data["order"] = order
        order += 1

        # Find and process all products
        product_files = find_series_products(series_key)
        products = {}
        prod_order = 1
        for pf in product_files:
            pdata = extract_product_data(pf, series_key)
            pdata["order"] = prod_order
            prod_order += 1
            products[pdata["slug"]] = pdata

        series_data["products"] = products
        catalog["series"][series_key] = series_data

    return catalog


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog()
    out_path = DATA_DIR / "catalog.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    # Print summary
    total_products = sum(
        len(s["products"]) for s in catalog["series"].values()
    )
    print(f"Catalog built: {len(catalog['series'])} series, {total_products} products")
    print(f"Written to: {out_path}")
    for key, s in catalog["series"].items():
        print(f"  {s['name']}: {len(s['products'])} products")


if __name__ == "__main__":
    main()

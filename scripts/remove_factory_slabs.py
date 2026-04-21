"""Remove factory slab images (showing machinery holding slabs) and renumber remaining slabs.

Based on the file name that was used when the slab was processed, we know which
slab-N.jpg came from a "Factory" photo. This script:
1. Deletes the factory slab files
2. Renumbers remaining slab files to remove gaps (slab.jpg, slab-2.jpg, ...)
3. Updates catalog.json
4. Regenerates all HTML pages
"""

import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

COLLECTIONS_DIR = PROJECT_DIR / "images" / "collections"
CATALOG_PATH = PROJECT_DIR / "admin" / "data" / "catalog.json"

# Mapping of (series_key, product_slug) -> filename of the factory slab to remove
# Derived from the process_slabs.py output (the Factory source photos).
FACTORY_SLABS_TO_REMOVE = {
    ("budget", "black-starlight"): "slab.jpg",
    ("budget", "cream-mirror"): "slab-2.jpg",
    ("budget", "crema"): "slab-2.jpg",
    ("budget", "grey-starlight"): "slab.jpg",
    ("budget", "grey-terrazo"): "slab-2.jpg",
    ("budget", "halo"): "slab-2.jpg",
    ("budget", "snowflake"): "slab.jpg",
    ("budget", "walnut"): "slab.jpg",
    ("budget", "white-terrazo"): "slab-2.jpg",
    ("calacatta", "alabama"): "slab-3.jpg",
    ("calacatta", "aspen-gold"): "slab-2.jpg",
    ("calacatta", "aurika"): "slab-2.jpg",
    ("calacatta", "avalanche"): "slab-2.jpg",
    ("calacatta", "everest-grey"): "slab-2.jpg",
    ("calacatta", "harmony-gold"): "slab.jpg",
    ("calacatta", "marquina-noir"): "slab-2.jpg",
    ("calacatta", "narina-gold"): "slab-2.jpg",
    ("calacatta", "narina-grey"): "slab-2.jpg",
    ("calacatta", "nova"): "slab-3.jpg",
    ("calacatta", "panda-white"): "slab-2.jpg",
    ("calacatta", "perla-venata"): "slab.jpg",
    ("calacatta", "sahara-noir"): "slab.jpg",
    ("calacatta", "vienna"): "slab-2.jpg",
    ("onyx", "crystal-ash"): "slab-2.jpg",
    ("onyx", "luminous-gold"): "slab-3.jpg",
    ("onyx", "marigold"): "slab-4.jpg",
    ("onyx", "nectar"): "slab-2.jpg",
    ("onyx", "trinity"): "slab-4.jpg",
    ("pastel", "mauve"): "slab-3.jpg",
    ("pastel", "peony"): "slab-2.jpg",
    ("pastel", "sage"): "slab-3.jpg",
    ("pastel", "seafoam"): "slab-2.jpg",
    ("carrara", "astral"): "slab-2.jpg",
    ("carrara", "aurum"): "slab.jpg",
    ("carrara", "bellagio"): "slab.jpg",
    ("carrara", "bianco-nova"): "slab-2.jpg",
    ("carrara", "blaze"): "slab.jpg",
    ("carrara", "fossil"): "slab-2.jpg",
    ("carrara", "gold-mine"): "slab-2.jpg",
    ("carrara", "orion-white"): "slab-2.jpg",
    ("carrara", "rayon"): "slab-2.jpg",
}


def main():
    catalog = json.loads(CATALOG_PATH.read_text())
    removed_count = 0
    renumbered_count = 0

    for (series_key, slug), factory_name in FACTORY_SLABS_TO_REMOVE.items():
        product_dir = COLLECTIONS_DIR / f"{series_key}-series" / slug
        factory_path = product_dir / factory_name

        if not factory_path.is_file():
            print(f"SKIP {series_key}/{slug}: {factory_name} not found")
            continue

        # Delete the factory slab
        factory_path.unlink()
        removed_count += 1
        print(f"Removed {series_key}/{slug}/{factory_name}")

        # Get all remaining slab files in order
        remaining = sorted(product_dir.glob("slab*.jpg"))

        # Renumber them to slab.jpg, slab-2.jpg, slab-3.jpg...
        # Use temp names first to avoid overwriting
        temp_names = []
        for i, path in enumerate(remaining):
            temp = product_dir / f"_tmp_slab_{i}.jpg"
            path.rename(temp)
            temp_names.append(temp)

        new_names = []
        for i, temp in enumerate(temp_names):
            if i == 0:
                final = product_dir / "slab.jpg"
            else:
                final = product_dir / f"slab-{i + 1}.jpg"
            temp.rename(final)
            new_names.append(final.name)

        # Update catalog for this product
        if series_key in catalog["series"] and slug in catalog["series"][series_key]["products"]:
            catalog["series"][series_key]["products"][slug]["slab_images"] = new_names
            renumbered_count += len(new_names)

    # Save catalog
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    # Regenerate HTML pages
    from admin.app import SITE_ROOT
    from admin.generators.product_page import render_product_page
    from admin.generators.series_page import render_series_page
    from admin.generators.domestic_page import render_domestic_page

    page_count = 0
    for sk, series in catalog["series"].items():
        html = render_series_page(sk, series)
        (SITE_ROOT / f"collection-domestic-{sk}.html").write_text(html, encoding="utf-8")
        page_count += 1
        for slug, product in series["products"].items():
            html = render_product_page(sk, series["name"], product)
            (SITE_ROOT / f"collection-domestic-{sk}-{slug}.html").write_text(html, encoding="utf-8")
            page_count += 1
    html = render_domestic_page(catalog)
    (SITE_ROOT / "collection-domestic.html").write_text(html, encoding="utf-8")
    page_count += 1

    print(f"\n{'=' * 50}")
    print(f"Removed {removed_count} factory slab images")
    print(f"Renumbered {renumbered_count} remaining slab files")
    print(f"Regenerated {page_count} HTML pages")


if __name__ == "__main__":
    main()

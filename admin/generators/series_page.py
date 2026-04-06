"""Generate series listing HTML pages from catalog data."""

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def render_series_page(series_key: str, series: dict) -> str:
    """Render a complete series listing HTML page."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template("series.html")

    filename = f"collection-domestic-{series_key}.html"

    # Sort products by order and add computed fields for template
    sorted_products = sorted(
        series["products"].values(),
        key=lambda p: p.get("order", 999),
    )
    for p in sorted_products:
        p["href"] = f"collection-domestic-{series_key}-{p['slug']}.html"
        p["card_image"] = f"images/collections/{series_key}-series/{p['slug']}/{p['render_images'][0]}" if p.get("render_images") else ""

    # Pick og:image from first product's render
    og_image = ""
    if sorted_products:
        first = sorted_products[0]
        og_image = first.get("card_image", "")

    return template.render(
        series_key=series_key,
        series=series,
        sorted_products=sorted_products,
        filename=filename,
        meta_description=f"{series['name']} - Premium quartz slabs by Glowstone. Explore our {series['name'].lower()} collection.",
        page_title=f"{series['name']} | Glowstone - Domestic Collection",
        og_title=f"{series['name']} | Glowstone - Domestic Collection",
        og_image=og_image,
    )

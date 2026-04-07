"""Generate individual product HTML pages from catalog data."""

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _carousel_id(slug: str) -> str:
    """Convert slug to camelCase carousel ID: 'aspen-gold' -> 'AspenGold'."""
    return "".join(w.capitalize() for w in slug.split("-"))


def _img_base(series_key: str, slug: str) -> str:
    return f"images/collections/{series_key}-series/{slug}"


def render_product_page(series_key: str, series_name: str, product: dict) -> str:
    """Render a complete product HTML page."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
        keep_trailing_newline=True,
    )
    template = env.get_template("product.html")

    slug = product["slug"]
    img_base = _img_base(series_key, slug)
    filename = f"collection-domestic-{series_key}-{slug}.html"

    # Pick og:image — first slab if available, else first render
    og_image = ""
    if product.get("slab_images"):
        og_image = f"{img_base}/{product['slab_images'][0]}"
    elif product.get("render_images"):
        og_image = f"{img_base}/{product['render_images'][0]}"

    return template.render(
        product=product,
        series_key=series_key,
        series_name=series_name,
        filename=filename,
        img_base=img_base,
        carousel_id=_carousel_id(slug),
        meta_description=f"{product['name']} - {series_name} by Glowstone. Premium engineered quartz surface.",
        page_title=f"{product['name']} | {series_name} | Glowstone",
        og_title=f"{product['name']} | {series_name} | Glowstone",
        og_image=og_image,
    )

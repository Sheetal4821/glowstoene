"""Generate the domestic collection landing page from catalog data."""

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def render_domestic_page(catalog: dict) -> str:
    """Render the collection-domestic.html page."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
        keep_trailing_newline=True,
    )
    template = env.get_template("domestic.html")

    # Build sorted series list
    series_list = []
    for key, s in catalog["series"].items():
        series_list.append({
            "key": key,
            "name": s["name"],
            "card_image": s.get("card_image", ""),
            "order": s.get("order", 999),
            "product_count": len(s.get("products", {})),
        })
    series_list.sort(key=lambda x: x["order"])

    return template.render(
        series_list=series_list,
        hero_image="images/collections/calacatta-series/perla-venata/render.png",
        filename="collection-domestic.html",
        meta_description="Glowstone Domestic Collection - Eternal Surfaces for India. Explore series: Onyx, Pastel, Plain, Calacatta, Budget, Carrara. Premium engineered quartz surfaces.",
        page_title="Domestic Collection | Glowstone - Eternal Surfaces India",
        og_title="Domestic Collection | Glowstone - Eternal Surfaces",
        og_image="images/collections/calacatta-series/perla-venata/render.png",
    )

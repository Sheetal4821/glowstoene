"""Glowstone Admin Panel - Flask Backend."""

import json
import os
import re
import shutil
import sys
from datetime import timedelta
from pathlib import Path

from flask import (
    Flask, jsonify, render_template, request, session,
)

# Allow importing from project scripts/
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from admin.config import (
    ALLOWED_EXTENSIONS, CATALOG_PATH, DATA_DIR, IMAGES_DIR,
    MAX_UPLOAD_SIZE_MB, ROOT_DIR as SITE_ROOT, SECRET_KEY,
    SESSION_LIFETIME_HOURS,
)
from admin.auth import check_password, password_is_set, set_password
from admin.generators.product_page import render_product_page
from admin.generators.series_page import render_series_page
from admin.generators.domestic_page import render_domestic_page

app = Flask(__name__, template_folder="templates")
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(hours=SESSION_LIFETIME_HOURS)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_catalog() -> dict:
    """Load catalog.json."""
    if not CATALOG_PATH.is_file():
        return {"series": {}}
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_catalog(catalog: dict) -> None:
    """Write catalog.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)


def slugify(name: str) -> str:
    """Convert a name to a URL-safe slug."""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def require_auth(f):
    """Decorator to require login."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def img_dir_for(series_key: str, slug: str) -> Path:
    """Get the image directory for a product."""
    return IMAGES_DIR / f"{series_key}-series" / slug


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def next_image_name(directory: Path, prefix: str, ext: str) -> str:
    """Find the next available image name (e.g. slab.jpg, slab-2.jpg, slab-3.jpg)."""
    base = f"{prefix}{ext}"
    if not (directory / base).exists():
        return base
    i = 2
    while True:
        name = f"{prefix}-{i}{ext}"
        if not (directory / name).exists():
            return name
        i += 1


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/admin")
def admin_page():
    """Serve the admin panel HTML."""
    return render_template("admin.html")


@app.route("/admin/login", methods=["POST"])
def login():
    """Authenticate with password."""
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    if not password_is_set():
        # First login — set the password
        if len(password) < 4:
            return jsonify({"error": "Password must be at least 4 characters"}), 400
        set_password(password)
        session.permanent = True
        session["authenticated"] = True
        return jsonify({"ok": True, "message": "Password set successfully"})

    if check_password(password):
        session.permanent = True
        session["authenticated"] = True
        return jsonify({"ok": True})

    return jsonify({"error": "Invalid password"}), 401


@app.route("/admin/logout", methods=["POST"])
def logout():
    """Clear session."""
    session.clear()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Catalog API
# ---------------------------------------------------------------------------

@app.route("/admin/api/catalog")
@require_auth
def get_catalog():
    """Return the full catalog."""
    return jsonify(load_catalog())


# ---------------------------------------------------------------------------
# Series CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/api/series", methods=["POST"])
@require_auth
def create_series():
    """Create a new series."""
    data = request.get_json(silent=True) or {}
    key = slugify(data.get("key", ""))
    name = data.get("name", "").strip()

    if not key or not name:
        return jsonify({"error": "Key and name are required"}), 400

    catalog = load_catalog()
    if key in catalog["series"]:
        return jsonify({"error": f"Series '{key}' already exists"}), 409

    max_order = max((s.get("order", 0) for s in catalog["series"].values()), default=0)
    catalog["series"][key] = {
        "name": name,
        "description": "",
        "hero_image": "",
        "card_image": "",
        "order": max_order + 1,
        "products": {},
    }
    save_catalog(catalog)
    return jsonify({"ok": True, "key": key})


@app.route("/admin/api/series/<key>", methods=["PUT"])
@require_auth
def update_series(key):
    """Update series metadata."""
    catalog = load_catalog()
    if key not in catalog["series"]:
        return jsonify({"error": "Series not found"}), 404

    data = request.get_json(silent=True) or {}
    series = catalog["series"][key]

    for field in ("name", "description", "hero_image", "card_image"):
        if field in data:
            series[field] = data[field]
    if "order" in data:
        series["order"] = int(data["order"])

    save_catalog(catalog)
    return jsonify({"ok": True})


@app.route("/admin/api/series/<key>", methods=["DELETE"])
@require_auth
def delete_series(key):
    """Delete a series and all its products/pages."""
    catalog = load_catalog()
    if key not in catalog["series"]:
        return jsonify({"error": "Series not found"}), 404

    series = catalog["series"][key]

    # Delete product HTML files
    for slug in series.get("products", {}):
        html_file = SITE_ROOT / f"collection-domestic-{key}-{slug}.html"
        if html_file.is_file():
            html_file.unlink()

    # Delete series HTML file
    series_html = SITE_ROOT / f"collection-domestic-{key}.html"
    if series_html.is_file():
        series_html.unlink()

    # Delete image directory
    series_img_dir = IMAGES_DIR / f"{key}-series"
    if series_img_dir.is_dir():
        shutil.rmtree(series_img_dir)

    del catalog["series"][key]
    save_catalog(catalog)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Product CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/api/series/<series_key>/products", methods=["POST"])
@require_auth
def create_product(series_key):
    """Create a new product in a series."""
    catalog = load_catalog()
    if series_key not in catalog["series"]:
        return jsonify({"error": "Series not found"}), 404

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Product name is required"}), 400

    slug = slugify(name)
    products = catalog["series"][series_key]["products"]

    if slug in products:
        return jsonify({"error": f"Product '{slug}' already exists in this series"}), 409

    max_order = max((p.get("order", 0) for p in products.values()), default=0)
    products[slug] = {
        "name": name,
        "slug": slug,
        "description": "Premium engineered quartz for kitchens, vanities, and commercial use\u2014durable, low-maintenance, and consistent in colour.",
        "thickness": "20 mm & 30 mm (availability may vary by design \u2014 confirm with Glowstone).",
        "size": "Jumbo 323 \u00d7 163 cm \u00b7 Super Jumbo 350 \u00d7 200 cm (nominal slab formats).",
        "slab_images": [],
        "render_images": [],
        "order": max_order + 1,
    }

    # Create image directory
    img_dir = img_dir_for(series_key, slug)
    img_dir.mkdir(parents=True, exist_ok=True)

    save_catalog(catalog)
    return jsonify({"ok": True, "slug": slug})


@app.route("/admin/api/series/<series_key>/products/<slug>", methods=["PUT"])
@require_auth
def update_product(series_key, slug):
    """Update product metadata."""
    catalog = load_catalog()
    if series_key not in catalog["series"]:
        return jsonify({"error": "Series not found"}), 404

    products = catalog["series"][series_key]["products"]
    if slug not in products:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json(silent=True) or {}
    product = products[slug]

    for field in ("name", "description", "thickness", "size"):
        if field in data:
            product[field] = data[field]
    if "order" in data:
        product["order"] = int(data["order"])

    save_catalog(catalog)
    return jsonify({"ok": True})


@app.route("/admin/api/series/<series_key>/products/<slug>", methods=["DELETE"])
@require_auth
def delete_product(series_key, slug):
    """Delete a product and its files."""
    catalog = load_catalog()
    if series_key not in catalog["series"]:
        return jsonify({"error": "Series not found"}), 404

    products = catalog["series"][series_key]["products"]
    if slug not in products:
        return jsonify({"error": "Product not found"}), 404

    # Delete HTML file
    html_file = SITE_ROOT / f"collection-domestic-{series_key}-{slug}.html"
    if html_file.is_file():
        html_file.unlink()

    # Delete image directory
    img_dir = img_dir_for(series_key, slug)
    if img_dir.is_dir():
        shutil.rmtree(img_dir)

    del products[slug]
    save_catalog(catalog)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Image upload / delete
# ---------------------------------------------------------------------------

@app.route("/admin/api/upload/slab/<series_key>/<slug>", methods=["POST"])
@require_auth
def upload_slab(series_key, slug):
    """Upload slab image(s) for a product."""
    catalog = load_catalog()
    if series_key not in catalog["series"]:
        return jsonify({"error": "Series not found"}), 404
    products = catalog["series"][series_key]["products"]
    if slug not in products:
        return jsonify({"error": "Product not found"}), 404

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    img_dir = img_dir_for(series_key, slug)
    img_dir.mkdir(parents=True, exist_ok=True)

    uploaded = []
    for f in files:
        if not f.filename or not allowed_file(f.filename):
            continue

        # Try to use slab_common for processing
        try:
            from slab_common import process_to_jpeg
            import tempfile
            ext_in = Path(f.filename).suffix.lower()
            with tempfile.NamedTemporaryFile(suffix=ext_in, delete=False) as tmp:
                f.save(tmp.name)
                out_name = next_image_name(img_dir, "slab", ".jpg")
                dest = img_dir / out_name
                process_to_jpeg(Path(tmp.name), dest)
                os.unlink(tmp.name)
        except ImportError:
            # Fallback: save as-is
            out_name = next_image_name(img_dir, "slab", ".jpg")
            dest = img_dir / out_name
            f.save(str(dest))

        uploaded.append(out_name)

    # Update catalog
    product = products[slug]
    product["slab_images"] = sorted(
        set(product.get("slab_images", []) + uploaded),
        key=lambda n: (0, 0) if n.split(".")[0] == "slab" else (1, int(re.search(r"(\d+)", n).group(1)) if re.search(r"(\d+)", n) else 0),
    )
    save_catalog(catalog)

    return jsonify({"ok": True, "uploaded": uploaded, "slab_images": product["slab_images"]})


@app.route("/admin/api/upload/render/<series_key>/<slug>", methods=["POST"])
@require_auth
def upload_render(series_key, slug):
    """Upload render image(s) for a product."""
    catalog = load_catalog()
    if series_key not in catalog["series"]:
        return jsonify({"error": "Series not found"}), 404
    products = catalog["series"][series_key]["products"]
    if slug not in products:
        return jsonify({"error": "Product not found"}), 404

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    img_dir = img_dir_for(series_key, slug)
    img_dir.mkdir(parents=True, exist_ok=True)

    uploaded = []
    for f in files:
        if not f.filename or not allowed_file(f.filename):
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg"):
            ext = ".png"
        out_name = next_image_name(img_dir, "render", ext)
        dest = img_dir / out_name
        f.save(str(dest))
        uploaded.append(out_name)

    # Update catalog
    product = products[slug]
    product["render_images"] = sorted(
        set(product.get("render_images", []) + uploaded),
        key=lambda n: (0, 0) if n.rsplit(".", 1)[0] == "render" else (1, int(re.search(r"(\d+)", n).group(1)) if re.search(r"(\d+)", n) else 0),
    )
    save_catalog(catalog)

    return jsonify({"ok": True, "uploaded": uploaded, "render_images": product["render_images"]})


@app.route("/admin/api/image/<img_type>/<series_key>/<slug>/<filename>", methods=["DELETE"])
@require_auth
def delete_image(img_type, series_key, slug, filename):
    """Delete a specific image file."""
    catalog = load_catalog()
    if series_key not in catalog["series"]:
        return jsonify({"error": "Series not found"}), 404
    products = catalog["series"][series_key]["products"]
    if slug not in products:
        return jsonify({"error": "Product not found"}), 404

    # Validate filename (prevent path traversal)
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"error": "Invalid filename"}), 400

    img_path = img_dir_for(series_key, slug) / filename
    if img_path.is_file():
        img_path.unlink()

    # Update catalog
    product = products[slug]
    list_key = "slab_images" if img_type == "slab" else "render_images"
    if filename in product.get(list_key, []):
        product[list_key].remove(filename)
    save_catalog(catalog)

    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Page regeneration
# ---------------------------------------------------------------------------

@app.route("/admin/api/regenerate", methods=["POST"])
@require_auth
def regenerate_all():
    """Regenerate all HTML pages from catalog."""
    catalog = load_catalog()
    log = []

    for series_key, series in catalog["series"].items():
        # Generate series page
        try:
            html = render_series_page(series_key, series)
            out = SITE_ROOT / f"collection-domestic-{series_key}.html"
            out.write_text(html, encoding="utf-8")
            log.append(f"Generated {out.name}")
        except Exception as e:
            log.append(f"Error generating {series_key} series page")

        # Generate product pages
        for slug, product in series["products"].items():
            try:
                html = render_product_page(series_key, series["name"], product)
                out = SITE_ROOT / f"collection-domestic-{series_key}-{slug}.html"
                out.write_text(html, encoding="utf-8")
                log.append(f"Generated {out.name}")
            except Exception as e:
                log.append(f"Error generating {series_key}/{slug}: {e}")

    # Generate domestic collection page
    try:
        html = render_domestic_page(catalog)
        out = SITE_ROOT / "collection-domestic.html"
        out.write_text(html, encoding="utf-8")
        log.append("Generated collection-domestic.html")
    except Exception as e:
        log.append(f"Error generating domestic page: {e}")

    return jsonify({"ok": True, "log": log})


@app.route("/admin/api/regenerate/<series_key>", methods=["POST"])
@require_auth
def regenerate_series(series_key):
    """Regenerate a specific series and its product pages."""
    catalog = load_catalog()
    if series_key not in catalog["series"]:
        return jsonify({"error": "Series not found"}), 404

    series = catalog["series"][series_key]
    log = []

    # Series page
    try:
        html = render_series_page(series_key, series)
        out = SITE_ROOT / f"collection-domestic-{series_key}.html"
        out.write_text(html, encoding="utf-8")
        log.append(f"Generated {out.name}")
    except Exception as e:
        log.append(f"Error generating series page: {e}")

    # Product pages
    for slug, product in series["products"].items():
        try:
            html = render_product_page(series_key, series["name"], product)
            out = SITE_ROOT / f"collection-domestic-{series_key}-{slug}.html"
            out.write_text(html, encoding="utf-8")
            log.append(f"Generated {out.name}")
        except Exception as e:
            log.append(f"Error generating {slug}: {e}")

    # Also regenerate domestic page (series cards may have changed)
    try:
        html = render_domestic_page(catalog)
        out = SITE_ROOT / "collection-domestic.html"
        out.write_text(html, encoding="utf-8")
        log.append("Generated collection-domestic.html")
    except Exception as e:
        log.append(f"Error generating domestic page: {e}")

    return jsonify({"ok": True, "log": log})


# ---------------------------------------------------------------------------
# Static file serving (for development — images, css, js from site root)
# ---------------------------------------------------------------------------

from flask import send_from_directory

@app.route("/images/<path:filepath>")
def serve_images(filepath):
    """Serve images from the site root (dev only)."""
    return send_from_directory(str(SITE_ROOT / "images"), filepath)

@app.route("/css/<path:filepath>")
def serve_css(filepath):
    return send_from_directory(str(SITE_ROOT / "css"), filepath)

@app.route("/js/<path:filepath>")
def serve_js(filepath):
    return send_from_directory(str(SITE_ROOT / "js"), filepath)

@app.route("/logo-2.avif")
def serve_logo():
    return send_from_directory(str(SITE_ROOT), "logo-2.avif")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Glowstone Admin Panel")
    parser.add_argument("--set-password", action="store_true", help="Set admin password")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    args = parser.parse_args()

    if args.set_password:
        import getpass
        pw = getpass.getpass("Enter new admin password: ")
        if len(pw) < 4:
            print("Password must be at least 4 characters.")
            sys.exit(1)
        set_password(pw)
        print("Password set successfully.")
        sys.exit(0)

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not password_is_set():
        print("No password set. The first login will set the admin password.")

    if not CATALOG_PATH.is_file():
        print(f"Warning: {CATALOG_PATH} not found. Run init_catalog.py first.")

    print(f"Starting admin panel at http://{args.host}:{args.port}/admin")
    app.run(host=args.host, port=args.port, debug=os.environ.get("FLASK_ENV") == "development")


if __name__ == "__main__":
    main()

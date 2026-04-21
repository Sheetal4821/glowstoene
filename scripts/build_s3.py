"""Build a clean S3-ready deployment package.

Creates:
  - s3-upload/     — folder with only production-ready static files
  - s3-upload.zip  — zipped version for upload

Excludes:
  - admin/ (Flask backend — not needed for static hosting)
  - scripts/ (Python scripts)
  - files/serises/ (raw source files)
  - .git, .gitignore, __pycache__
  - README.md, .DS_Store, Untitled, etc.

Run on your Mac:
    cd ~/Desktop/glowstoene
    python3 scripts/build_s3.py
"""

import shutil
import zipfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
BUILD_DIR = PROJECT_DIR / "s3-upload"
ZIP_PATH = PROJECT_DIR / "s3-upload.zip"

# Include these top-level files
INCLUDE_FILES = [
    "*.html",
    "robots.txt",
    "sitemap.xml",
    "logo-2.avif",
]

# Include these folders (will copy recursively)
INCLUDE_DIRS = [
    "css",
    "js",
    "images",
    "files",
]

# Skip these paths/patterns inside included folders
SKIP_PATTERNS = [
    "files/serises",      # raw source files (not needed)
    "files/Untitled",     # empty file
    "__pycache__",
    ".DS_Store",
    ".AppleDouble",
    ".LSOverride",
    "._",
]


def should_skip(path: Path) -> bool:
    path_str = str(path)
    for pattern in SKIP_PATTERNS:
        if pattern in path_str:
            return True
    if path.name.startswith("._") or path.name == ".DS_Store":
        return True
    return False


def copy_included():
    """Copy all production files into s3-upload/."""
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir()

    # Copy top-level files
    for pattern in INCLUDE_FILES:
        for f in PROJECT_DIR.glob(pattern):
            if f.is_file() and not should_skip(f):
                shutil.copy2(f, BUILD_DIR / f.name)

    # Copy included folders
    for folder in INCLUDE_DIRS:
        src = PROJECT_DIR / folder
        if not src.is_dir():
            continue
        dst = BUILD_DIR / folder

        def copy_filter(dir, names):
            # shutil.copytree ignore function — return list of names to skip
            ignored = []
            for name in names:
                full = Path(dir) / name
                if should_skip(full):
                    ignored.append(name)
            return ignored

        shutil.copytree(src, dst, ignore=copy_filter)


def make_zip():
    """Create s3-upload.zip from the build directory."""
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in BUILD_DIR.rglob("*"):
            if f.is_file():
                arcname = f.relative_to(BUILD_DIR)
                zf.write(f, arcname)


def print_summary():
    # Count files and total size
    total_files = 0
    total_bytes = 0
    for f in BUILD_DIR.rglob("*"):
        if f.is_file():
            total_files += 1
            total_bytes += f.stat().st_size
    zip_size = ZIP_PATH.stat().st_size

    print(f"\n{'=' * 60}")
    print(f"Build complete!")
    print(f"\nFolder:  {BUILD_DIR}")
    print(f"  Files: {total_files}")
    print(f"  Size:  {total_bytes / 1024 / 1024:.1f} MB")
    print(f"\nZip:     {ZIP_PATH}")
    print(f"  Size:  {zip_size / 1024 / 1024:.1f} MB")
    print(f"\nNext steps:")
    print(f"  1. Go to AWS S3 console: https://s3.console.aws.amazon.com/")
    print(f"  2. Create a new bucket (e.g. 'glowstone-preview')")
    print(f"  3. In bucket settings -> Properties -> enable 'Static website hosting'")
    print(f"     Index document: index.html")
    print(f"  4. In bucket settings -> Permissions:")
    print(f"     - Uncheck 'Block all public access'")
    print(f"     - Add a public read bucket policy (see AWS docs)")
    print(f"  5. Upload either:")
    print(f"     - the s3-upload.zip (S3 will need to be unzipped first)")
    print(f"     - OR drag-drop the contents of s3-upload/ folder directly")
    print(f"  6. Share the bucket's website URL with your senior.")


def main():
    print("Building S3 deployment package...")
    copy_included()
    print(f"Copied files to {BUILD_DIR}")
    make_zip()
    print(f"Created {ZIP_PATH}")
    print_summary()


if __name__ == "__main__":
    main()

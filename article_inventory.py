from pathlib import Path
import html
import json
import re
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parent
ARTICLES_DIR = PROJECT_ROOT / "articles"

SITE_URL = "https://domanid.com"


def _extract(pattern, text, default=""):
    match = re.search(
        pattern,
        text,
        flags=re.I | re.S,
    )

    if not match:
        return default

    return html.unescape(
        match.group(1).strip()
    )


def _clean_title(title):
    suffixes = [
        " - DomanID",
        " | DomanID",
    ]

    for suffix in suffixes:
        if title.endswith(suffix):
            title = title[:-len(suffix)].strip()

    return title


def _extract_json_ld_date(text):
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>'
        r'(.*?)'
        r'</script>',
        text,
        flags=re.I | re.S,
    )

    for raw in scripts:
        try:
            payload = json.loads(raw)
        except Exception:
            continue

        objects = (
            payload
            if isinstance(payload, list)
            else [payload]
        )

        for obj in objects:
            if not isinstance(obj, dict):
                continue

            date = str(
                obj.get(
                    "datePublished",
                    "",
                )
            ).strip()

            if date:
                return date

    return ""


def _normalize_date(value):
    value = str(value or "").strip()

    if not value:
        return ""

    # Keep standard ISO date.
    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        value,
    )

    if match:
        return match.group(1)

    # Try a few legacy formats.
    formats = [
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(
                value,
                fmt,
            )
            return dt.strftime(
                "%Y-%m-%d"
            )
        except ValueError:
            pass

    return value


def read_article(path):
    text = path.read_text(
        encoding="utf-8",
        errors="strict",
    )

    title = _extract(
        r"<title>(.*?)</title>",
        text,
    )
    title = _clean_title(title)

    description = _extract(
        r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
        text,
    )

    if not description:
        description = _extract(
            r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']',
            text,
        )

    canonical = _extract(
        r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']',
        text,
    )

    if not canonical:
        canonical = (
            f"{SITE_URL}/articles/"
            f"{path.name}"
        )

    date = _extract_json_ld_date(
        text
    )

    # Legacy articles may not contain datePublished
    # in JSON-LD. Fall back to the visible article-meta
    # value, e.g. "Technology | 2026-03-22".
    if not date:
        meta_match = re.search(
            r'<span[^>]*class=["\']article-meta["\'][^>]*>'
            r'.*?(\d{4}-\d{2}-\d{2}).*?'
            r'</span>',
            text,
            flags=re.I | re.S,
        )

        if meta_match:
            date = meta_match.group(1)

    date = _normalize_date(
        date
    )

    category = _extract(
        r'<span[^>]*class=["\']article-category["\'][^>]*>'
        r'(.*?)'
        r'</span>',
        text,
    )

    # Legacy articles store category and date together:
    # <span class="article-meta">Technology | 2026-03-22</span>
    if not category:
        category_match = re.search(
            r'<span[^>]*class=["\']article-meta["\'][^>]*>'
            r'\s*([^<|]+?)\s*\|\s*\d{4}-\d{2}-\d{2}'
            r'.*?</span>',
            text,
            flags=re.I | re.S,
        )

        if category_match:
            category = html.unescape(
                category_match.group(1).strip()
            )

    if not category:
        category = "Domain Insights"

    return {
        "filename": path.name,
        "slug": path.stem,
        "title": title,
        "excerpt": description,
        "description": description,
        "date": date,
        "category": category,
        "canonical": canonical,
        "path": str(path),
    }


def load_articles():
    if not ARTICLES_DIR.exists():
        raise RuntimeError(
            "articles directory not found"
        )

    articles = []

    for path in sorted(
        ARTICLES_DIR.glob("*.html")
    ):
        if path.name.lower() == "index.html":
            continue

        article = read_article(
            path
        )

        articles.append(
            article
        )

    articles.sort(
        key=lambda item: (
            item.get("date", ""),
            item.get("slug", ""),
        ),
        reverse=True,
    )

    return articles


def validate_articles(articles):
    errors = []

    seen_files = set()
    seen_canonicals = set()

    for article in articles:
        filename = article["filename"]

        if filename in seen_files:
            errors.append(
                f"Duplicate filename: {filename}"
            )

        seen_files.add(
            filename
        )

        if not article["title"]:
            errors.append(
                f"Missing title: {filename}"
            )

        if not article["excerpt"]:
            errors.append(
                f"Missing description: {filename}"
            )

        if not article["date"]:
            errors.append(
                f"Missing publication date: {filename}"
            )

        canonical = article["canonical"]

        if not canonical:
            errors.append(
                f"Missing canonical: {filename}"
            )
        elif canonical in seen_canonicals:
            errors.append(
                f"Duplicate canonical: {canonical}"
            )

        seen_canonicals.add(
            canonical
        )

    return errors


if __name__ == "__main__":
    articles = load_articles()

    errors = validate_articles(
        articles
    )

    print(
        "ARTICLE INVENTORY:",
        len(articles),
    )

    dated = sum(
        1
        for article in articles
        if article["date"]
    )

    described = sum(
        1
        for article in articles
        if article["excerpt"]
    )

    print(
        "WITH DATE        :",
        dated,
    )

    print(
        "WITH DESCRIPTION :",
        described,
    )

    print(
        "VALIDATION ERRORS:",
        len(errors),
    )

    if errors:
        print()
        print("ERRORS:")

        for error in errors:
            print(
                " -",
                error,
            )

        raise SystemExit(1)

    print()
    print("[PASS] Article inventory is valid.")

    print()
    print("LATEST 5:")

    for article in articles[:5]:
        print(
            f'  {article["date"]} | '
            f'{article["filename"]}'
        )

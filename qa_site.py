from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parent

DOMAINS_FILE = PROJECT_ROOT / "data" / "domains.json"
DOMAINS_DIR = PROJECT_ROOT / "domains"
ARTICLES_DIR = PROJECT_ROOT / "articles"

INDEX_FILE = PROJECT_ROOT / "index.html"
SITEMAP_FILE = PROJECT_ROOT / "sitemap.xml"
RSS_FILE = PROJECT_ROOT / "rss.xml"

SITE_URL = "https://domanid.com"


errors: list[str] = []
warnings: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def warn(message: str) -> None:
    warnings.append(message)


def read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="strict",
        )
    except Exception as exc:
        fail(
            f"Cannot read {path.relative_to(PROJECT_ROOT)}: "
            f"{exc}"
        )
        return ""


def load_domains() -> list[dict]:
    if not DOMAINS_FILE.exists():
        fail("data/domains.json is missing.")
        return []

    try:
        payload = json.loads(
            DOMAINS_FILE.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        fail(
            f"Invalid domains.json: {exc}"
        )
        return []

    domains = payload.get("domains")

    if not isinstance(domains, list):
        fail(
            "domains.json field 'domains' "
            "must be a list."
        )
        return []

    return [
        d
        for d in domains
        if str(
            d.get("status", "")
        ).strip().lower()
        == "active"
    ]


def check_required_files() -> None:
    required = [
        INDEX_FILE,
        SITEMAP_FILE,
        RSS_FILE,
        PROJECT_ROOT / "robots.txt",
        PROJECT_ROOT / "CNAME",
        PROJECT_ROOT / "style.css",
        PROJECT_ROOT / "app.js",
        ARTICLES_DIR / "index.html",
    ]

    for path in required:
        if not path.exists():
            fail(
                "Missing required file: "
                f"{path.relative_to(PROJECT_ROOT)}"
            )


def check_domain_inventory(
    domains: list[dict],
) -> set[str]:

    slugs: set[str] = set()
    names: set[str] = set()

    for domain in domains:
        name = str(
            domain.get("domain", "")
        ).strip()

        slug = str(
            domain.get("slug", "")
        ).strip()

        if not name:
            fail(
                "Active domain with missing domain name."
            )

        if not slug:
            fail(
                f"Missing slug for domain: {name}"
            )
            continue

        if name in names:
            fail(
                f"Duplicate domain: {name}"
            )

        if slug in slugs:
            fail(
                f"Duplicate slug: {slug}"
            )

        names.add(name)
        slugs.add(slug)

    return slugs


def extract_json_ld(
    html: str,
    source: str,
) -> list[dict]:

    blocks = re.findall(
        r'<script\s+type=["\']application/ld\+json["\']'
        r'[^>]*>\s*(.*?)\s*</script>',
        html,
        flags=re.I | re.S,
    )

    parsed: list[dict] = []

    for index, block in enumerate(
        blocks,
        start=1,
    ):
        try:
            data = json.loads(block)

            if isinstance(data, dict):
                parsed.append(data)

        except Exception as exc:
            fail(
                f"Invalid JSON-LD in {source} "
                f"(block {index}): {exc}"
            )

    return parsed


def check_domain_pages(
    domains: list[dict],
    active_slugs: set[str],
) -> None:

    existing_slugs = {
        p.name
        for p in DOMAINS_DIR.iterdir()
        if p.is_dir()
    } if DOMAINS_DIR.exists() else set()

    missing = (
        active_slugs
        - existing_slugs
    )

    obsolete = (
        existing_slugs
        - active_slugs
    )

    for slug in sorted(missing):
        fail(
            f"Missing domain page: domains/{slug}/"
        )

    for slug in sorted(obsolete):
        fail(
            f"Obsolete domain page remains: "
            f"domains/{slug}/"
        )

    domain_by_slug = {
        str(d.get("slug", "")).strip(): d
        for d in domains
    }

    for slug in sorted(active_slugs):
        page = (
            DOMAINS_DIR
            / slug
            / "index.html"
        )

        if not page.exists():
            continue

        html = read_text(page)

        if not html:
            continue

        name = str(
            domain_by_slug[slug].get(
                "domain",
                "",
            )
        ).strip()

        source = f"domains/{slug}/index.html"

        if not re.search(
            r"<title>.+?</title>",
            html,
            flags=re.I | re.S,
        ):
            fail(
                f"Missing title: {source}"
            )

        if not re.search(
            r'<meta\s+name=["\']description["\']',
            html,
            flags=re.I,
        ):
            fail(
                f"Missing meta description: {source}"
            )

        if not re.search(
            r"<h1\b[^>]*>.*?</h1>",
            html,
            flags=re.I | re.S,
        ):
            fail(
                f"Missing H1: {source}"
            )

        canonical_expected = (
            f"{SITE_URL}/domains/{slug}/"
        )

        canonical_match = re.search(
            r'<link\s+rel=["\']canonical["\']'
            r'\s+href=["\']([^"\']+)["\']',
            html,
            flags=re.I,
        )

        if not canonical_match:
            fail(
                f"Missing canonical: {source}"
            )

        elif (
            canonical_match.group(1)
            != canonical_expected
        ):
            fail(
                f"Wrong canonical in {source}: "
                f"{canonical_match.group(1)}"
            )

        placeholders = re.findall(
            r"\{\{\s*[A-Z0-9_]+\s*\}\}",
            html,
            flags=re.I,
        )

        if placeholders:
            fail(
                f"Template placeholder remains in {source}: "
                + ", ".join(sorted(set(placeholders)))
            )

        json_ld = extract_json_ld(
            html,
            source,
        )

        found_product = False
        found_breadcrumb = False

        for block in json_ld:
            graph = block.get(
                "@graph",
                [],
            )

            if not isinstance(graph, list):
                graph = [block]

            for item in graph:
                if not isinstance(item, dict):
                    continue

                item_type = item.get(
                    "@type"
                )

                if item_type == "Product":
                    found_product = True

                if (
                    item_type
                    == "BreadcrumbList"
                ):
                    found_breadcrumb = True

        if not found_product:
            fail(
                f"Product JSON-LD missing: {source}"
            )

        if not found_breadcrumb:
            fail(
                f"Breadcrumb JSON-LD missing: {source}"
            )

        if name not in html:
            warn(
                f"Domain name not found verbatim "
                f"in page: {source}"
            )


def check_article_blocks(
    active_slugs: set[str],
) -> tuple[int, int]:

    articles = [
        path
        for path in ARTICLES_DIR.glob(
            "*.html"
        )
        if path.name.lower()
        != "index.html"
    ]

    managed = 0

    for path in articles:
        html = read_text(path)

        starts = html.count(
            "DOMANID_RELATED_DOMAINS_START"
        )

        ends = html.count(
            "DOMANID_RELATED_DOMAINS_END"
        )

        if starts != ends:
            fail(
                f"Managed markers mismatch: "
                f"articles/{path.name}"
            )

        if starts > 1:
            fail(
                f"Duplicate managed block: "
                f"articles/{path.name}"
            )

        if starts == 1:
            managed += 1

        placeholders = re.findall(
            r"\{\{\s*[A-Z0-9_]+\s*\}\}",
            html,
            flags=re.I,
        )

        if placeholders:
            fail(
                f"Template placeholder remains in "
                f"articles/{path.name}: "
                + ", ".join(sorted(set(placeholders)))
            )

        for slug in re.findall(
            r'href=["\']\.\./domains/([^/"\']+)/["\']',
            html,
            flags=re.I,
        ):
            if slug not in active_slugs:
                fail(
                    "Article links to inactive or "
                    f"missing domain: "
                    f"articles/{path.name} -> "
                    f"{slug}"
                )

            target = (
                DOMAINS_DIR
                / slug
                / "index.html"
            )

            if not target.exists():
                fail(
                    "Broken domain link: "
                    f"articles/{path.name} -> "
                    f"domains/{slug}/"
                )

    return (
        len(articles),
        managed,
    )


def check_homepage(
    domains: list[dict],
) -> int:
    """
    Homepage is intentionally Premium-only.

    Only featured domains should appear as domain cards.
    The complete active inventory lives under /domains/.
    """

    if not INDEX_FILE.exists():
        return 0

    html = read_text(
        INDEX_FILE
    )

    featured_domains = [
        domain
        for domain in domains
        if bool(
            domain.get("featured")
        )
    ]

    expected_cards = len(
        featured_domains
    )

    found_cards = html.count(
        'class="domain-card glass-panel'
    )

    if found_cards != expected_cards:
        fail(
            "Homepage premium card count mismatch: "
            f"expected {expected_cards}, "
            f"found {found_cards}"
        )

    for domain in featured_domains:
        slug = str(
            domain.get("slug", "")
        ).strip()

        if not slug:
            continue

        if (
            f'href="domains/{slug}/"'
            not in html
        ):
            fail(
                "Homepage missing featured domain link: "
                f"{slug}"
            )

    if 'href="domains/"' not in html:
        fail(
            "Homepage missing full domains "
            "inventory link."
        )

    return found_cards


def check_domains_inventory(
    domains: list[dict],
) -> int:
    """
    Validate the complete public domain inventory page.
    """

    inventory_file = (
        PROJECT_ROOT
        / "domains"
        / "index.html"
    )

    if not inventory_file.exists():
        fail(
            "Full domains inventory page is missing: "
            "domains/index.html"
        )
        return 0

    html = read_text(
        inventory_file
    )

    expected_cards = len(
        domains
    )

    found_cards = len(
        re.findall(
            r'class=["\']inventory-card'
            r'(?:\s+inventory-card-premium)?["\']',
            html,
            flags=re.I,
        )
    )

    if found_cards != expected_cards:
        fail(
            "Domain inventory card count mismatch: "
            f"expected {expected_cards}, "
            f"found {found_cards}"
        )

    expected_premium = sum(
        1
        for domain in domains
        if bool(
            domain.get("featured")
        )
    )

    found_premium = html.count(
        'class="inventory-card '
        'inventory-card-premium"'
    )

    if found_premium != expected_premium:
        fail(
            "Domain inventory premium count mismatch: "
            f"expected {expected_premium}, "
            f"found {found_premium}"
        )

    for domain in domains:
        slug = str(
            domain.get("slug", "")
        ).strip()

        if not slug:
            continue

        if (
            f'href="{slug}/"'
            not in html
        ):
            fail(
                "Domain inventory missing domain link: "
                f"{slug}"
            )

    placeholders = re.findall(
        r"\{\{\s*[A-Z0-9_]+\s*\}\}",
        html,
        flags=re.I,
    )

    if placeholders:
        fail(
            "Template placeholder remains in "
            "domains/index.html: "
            + ", ".join(
                sorted(
                    set(placeholders)
                )
            )
        )

    canonical = (
        f'{SITE_URL}/domains/'
    )

    if (
        f'href="{canonical}"'
        not in html
    ):
        fail(
            "Wrong or missing canonical in "
            "domains/index.html"
        )

    return found_cards


def check_sitemap(
    active_slugs: set[str],
) -> None:

    if not SITEMAP_FILE.exists():
        return

    xml = read_text(
        SITEMAP_FILE
    )

    urls = re.findall(
        r"<loc>(.*?)</loc>",
        xml,
        flags=re.I | re.S,
    )

    normalized = [
        url.strip()
        for url in urls
    ]

    if len(normalized) != len(
        set(normalized)
    ):
        fail(
            "Duplicate URLs found in sitemap.xml"
        )

    sitemap_slugs = set()

    for url in normalized:
        match = re.search(
            r"/domains/([^/]+)/?$",
            url,
        )

        if match:
            sitemap_slugs.add(
                match.group(1)
            )

    missing = (
        active_slugs
        - sitemap_slugs
    )

    obsolete = (
        sitemap_slugs
        - active_slugs
    )

    for slug in sorted(missing):
        fail(
            f"Domain missing from sitemap: {slug}"
        )

    for slug in sorted(obsolete):
        fail(
            f"Inactive domain remains in sitemap: "
            f"{slug}"
        )


def check_local_links() -> int:
    excluded_templates = {
        (PROJECT_ROOT / "article_template.html").resolve(),
        (
            PROJECT_ROOT
            / "templates"
            / "index_template.html"
        ).resolve(),
        (
            PROJECT_ROOT
            / "templates"
            / "domains_index_template.html"
        ).resolve(),
    }

    html_files = [
        path
        for path in PROJECT_ROOT.rglob(
            "*.html"
        )
        if ".git" not in path.parts
        and path.resolve() not in excluded_templates
    ]

    checked = 0

    for source in html_files:
        html = read_text(source)

        hrefs = re.findall(
            r'href=["\']([^"\']+)["\']',
            html,
            flags=re.I,
        )

        for href in hrefs:
            href = href.strip()

            if not href:
                continue

            if href.startswith(
                (
                    "http://",
                    "https://",
                    "mailto:",
                    "tel:",
                    "javascript:",
                    "#",
                )
            ):
                continue

            clean_href = href.split(
                "#",
                1,
            )[0].split(
                "?",
                1,
            )[0]

            if not clean_href:
                continue

            checked += 1

            if clean_href.startswith("/"):
                target = (
                    PROJECT_ROOT
                    / clean_href.lstrip("/")
                )

            else:
                target = (
                    source.parent
                    / clean_href
                )

            if clean_href.endswith("/"):
                target = (
                    target
                    / "index.html"
                )

            try:
                target = target.resolve()
            except Exception:
                continue

            if not target.exists():
                fail(
                    "Broken internal link: "
                    f"{source.relative_to(PROJECT_ROOT)} "
                    f"-> {href}"
                )

    return checked


def print_report(
    domains: list[dict],
    homepage_card_count: int,
    inventory_card_count: int,
    article_count: int,
    managed_count: int,
    links_checked: int,
) -> None:

    print()
    print("=" * 68)
    print("DomanID Automated QA")
    print("Phase 1J")
    print("=" * 68)

    print(
        f"Active domains         : "
        f"{len(domains)}"
    )

    print(
        f"Homepage premium cards : "
        f"{homepage_card_count}"
    )

    print(
        f"Inventory cards        : "
        f"{inventory_card_count}"
    )

    print(
        f"Article pages          : "
        f"{article_count}"
    )

    print(
        f"Managed article blocks : "
        f"{managed_count}"
    )

    print(
        f"Internal links checked : "
        f"{links_checked}"
    )

    print(
        f"Warnings               : "
        f"{len(warnings)}"
    )

    print(
        f"Errors                 : "
        f"{len(errors)}"
    )

    if warnings:
        print()
        print("WARNINGS:")

        for item in warnings:
            print(
                f"  [WARN] {item}"
            )

    if errors:
        print()
        print("ERRORS:")

        for item in errors:
            print(
                f"  [FAIL] {item}"
            )

        print()
        print(
            "[FAIL] Site QA failed."
        )

    else:
        print()
        print(
            "[PASS] Site QA completed successfully."
        )


def main() -> int:
    check_required_files()

    domains = load_domains()

    active_slugs = (
        check_domain_inventory(
            domains
        )
    )

    check_domain_pages(
        domains,
        active_slugs,
    )

    homepage_card_count = (
        check_homepage(
            domains
        )
    )

    inventory_card_count = (
        check_domains_inventory(
            domains
        )
    )

    article_count, managed_count = (
        check_article_blocks(
            active_slugs
        )
    )

    check_sitemap(
        active_slugs
    )

    links_checked = (
        check_local_links()
    )

    print_report(
        domains,
        homepage_card_count,
        inventory_card_count,
        article_count,
        managed_count,
        links_checked,
    )

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

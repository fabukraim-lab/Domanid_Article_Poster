"""
DomanID - Unified Site Build Pipeline
Phase 1I

Runs the complete local DomanID static-site build in the
required order and stops immediately if any stage fails.

Usage:

    python build_site.py

Optional:

    python build_site.py --skip-fetch

The --skip-fetch option uses the existing data/domains.json
instead of downloading the latest domain inventory.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

DOMAINS_JSON = PROJECT_ROOT / "data" / "domains.json"
DOMAINS_DIR = PROJECT_ROOT / "domains"
INDEX_FILE = PROJECT_ROOT / "index.html"
SITEMAP_FILE = PROJECT_ROOT / "sitemap.xml"
RSS_FILE = PROJECT_ROOT / "rss.xml"
ARTICLES_DIR = PROJECT_ROOT / "articles"


# ============================================================
# PIPELINE STAGES
# ============================================================

PIPELINE = [
    (
        "Domain inventory",
        [
            "generators/domain_data_loader.py",
        ],
    ),
    (
        "Domain pages",
        [
            "generators/domain_page_generator.py",
        ],
    ),
    (
        "Homepage",
        [
            "generators/homepage_generator.py",
        ],
    ),
    (
        "Article-domain links",
        [
            "inject_related_domains.py",
        ],
    ),
    (
        "SEO files",
        [
            "_gen_seo_files.py",
        ],
    ),
    (
        "Automated QA",
        [
            "qa_site.py",
        ],
    ),
]


# ============================================================
# HELPERS
# ============================================================


def run_stage(
    number: int,
    total: int,
    title: str,
    command: list[str],
) -> float:
    """
    Run one pipeline stage.

    The pipeline stops immediately if the subprocess
    returns a non-zero exit code.
    """
    print()
    print("=" * 68)
    print(
        f"[STAGE {number}/{total}] {title}"
    )
    print("=" * 68)

    display_command = " ".join(
        [sys.executable, *command]
    )

    print(
        f"[RUN] {display_command}"
    )
    print()

    started = time.perf_counter()

    result = subprocess.run(
        [
            sys.executable,
            *command,
        ],
        cwd=PROJECT_ROOT,
    )

    elapsed = time.perf_counter() - started

    if result.returncode != 0:
        print()
        print(
            f"[FAIL] {title}"
        )
        print(
            f"[FAIL] Exit code: "
            f"{result.returncode}"
        )
        print(
            "[STOP] Build aborted. "
            "Later stages were not executed."
        )

        raise SystemExit(
            result.returncode
        )

    print()
    print(
        f"[PASS] {title} "
        f"({elapsed:.2f}s)"
    )

    return elapsed


def load_domain_inventory() -> list[dict]:
    if not DOMAINS_JSON.exists():
        raise RuntimeError(
            "data/domains.json does not exist."
        )

    payload = json.loads(
        DOMAINS_JSON.read_text(
            encoding="utf-8"
        )
    )

    domains = payload.get(
        "domains"
    )

    if not isinstance(
        domains,
        list,
    ):
        raise RuntimeError(
            "Invalid domains.json: "
            "'domains' must be a list."
        )

    return domains


# ============================================================
# VALIDATION
# ============================================================


def validate_build() -> dict[str, int]:
    print()
    print("=" * 68)
    print("[VALIDATION] Final site checks")
    print("=" * 68)

    errors: list[str] = []

    # --------------------------------------------------------
    # Domain inventory
    # --------------------------------------------------------

    try:
        domains = load_domain_inventory()

    except Exception as exc:
        errors.append(
            f"Domain inventory invalid: {exc}"
        )

        domains = []

    active_domains = [
        domain
        for domain in domains
        if str(
            domain.get(
                "status",
                "",
            )
        ).strip().lower()
        == "active"
    ]

    active_slugs = {
        str(
            domain.get(
                "slug",
                "",
            )
        ).strip()
        for domain in active_domains
        if str(
            domain.get(
                "slug",
                "",
            )
        ).strip()
    }

    featured_count = sum(
        1
        for domain in active_domains
        if bool(
            domain.get(
                "featured"
            )
        )
    )

    # --------------------------------------------------------
    # Generated domain pages
    # --------------------------------------------------------

    existing_domain_dirs = set()

    if DOMAINS_DIR.exists():
        existing_domain_dirs = {
            item.name
            for item in DOMAINS_DIR.iterdir()
            if item.is_dir()
        }

    missing_pages = (
        active_slugs
        - existing_domain_dirs
    )

    obsolete_pages = (
        existing_domain_dirs
        - active_slugs
    )

    if missing_pages:
        errors.append(
            "Missing domain pages: "
            + ", ".join(
                sorted(
                    missing_pages
                )
            )
        )

    if obsolete_pages:
        errors.append(
            "Obsolete domain pages remain: "
            + ", ".join(
                sorted(
                    obsolete_pages
                )
            )
        )

    # --------------------------------------------------------
    # Homepage
    # --------------------------------------------------------

    if not INDEX_FILE.exists():
        errors.append(
            "index.html is missing."
        )

        homepage_text = ""

    else:
        homepage_text = (
            INDEX_FILE.read_text(
                encoding="utf-8"
            )
        )

    homepage_domain_cards = (
        homepage_text.count(
            'class="domain-card glass-panel'
        )
    )

    expected_homepage_cards = (
        len(active_domains)
        + featured_count
    )

    if (
        homepage_domain_cards
        != expected_homepage_cards
    ):
        errors.append(
            "Homepage domain-card count mismatch: "
            f"expected {expected_homepage_cards}, "
            f"found {homepage_domain_cards}."
        )

    # --------------------------------------------------------
    # Sitemap
    # --------------------------------------------------------

    if not SITEMAP_FILE.exists():
        errors.append(
            "sitemap.xml is missing."
        )

        sitemap_text = ""

    else:
        sitemap_text = (
            SITEMAP_FILE.read_text(
                encoding="utf-8"
            )
        )

    sitemap_domain_urls = (
        sitemap_text.count(
            "/domains/"
        )
    )

    if (
        sitemap_domain_urls
        != len(active_domains)
    ):
        errors.append(
            "Sitemap domain URL count mismatch: "
            f"expected {len(active_domains)}, "
            f"found {sitemap_domain_urls}."
        )

    # --------------------------------------------------------
    # Articles
    # --------------------------------------------------------

    article_files = []

    if ARTICLES_DIR.exists():
        article_files = [
            path
            for path in ARTICLES_DIR.glob(
                "*.html"
            )
            if path.name.lower()
            != "index.html"
        ]

    article_managed_blocks = 0

    for path in article_files:
        content = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        starts = content.count(
            "DOMANID_RELATED_DOMAINS_START"
        )

        ends = content.count(
            "DOMANID_RELATED_DOMAINS_END"
        )

        if starts != ends:
            errors.append(
                "Managed article block mismatch: "
                f"{path.name}"
            )

        if starts > 1:
            errors.append(
                "Duplicate related-domain block: "
                f"{path.name}"
            )

        if starts == 1:
            article_managed_blocks += 1

    # --------------------------------------------------------
    # RSS
    # --------------------------------------------------------

    if not RSS_FILE.exists():
        errors.append(
            "rss.xml is missing."
        )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    print(
        f"Active domains        : "
        f"{len(active_domains)}"
    )

    print(
        f"Featured domains      : "
        f"{featured_count}"
    )

    print(
        f"Domain directories    : "
        f"{len(existing_domain_dirs)}"
    )

    print(
        f"Homepage cards        : "
        f"{homepage_domain_cards}"
    )

    print(
        f"Sitemap domain URLs   : "
        f"{sitemap_domain_urls}"
    )

    print(
        f"Article pages         : "
        f"{len(article_files)}"
    )

    print(
        f"Managed article blocks: "
        f"{article_managed_blocks}"
    )

    if errors:
        print()
        print(
            f"[FAIL] Validation found "
            f"{len(errors)} problem(s):"
        )

        for error in errors:
            print(
                f"  - {error}"
            )

        raise SystemExit(1)

    print()
    print(
        "[PASS] Final site validation passed."
    )

    return {
        "active_domains": (
            len(active_domains)
        ),
        "featured_domains": (
            featured_count
        ),
        "domain_pages": (
            len(existing_domain_dirs)
        ),
        "homepage_cards": (
            homepage_domain_cards
        ),
        "sitemap_domains": (
            sitemap_domain_urls
        ),
        "articles": (
            len(article_files)
        ),
        "managed_articles": (
            article_managed_blocks
        ),
    }


# ============================================================
# MAIN
# ============================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the complete DomanID "
            "static website."
        )
    )

    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help=(
            "Skip Google Sheets domain fetch "
            "and use existing domains.json."
        ),
    )

    parser.add_argument(
        "--daily",
        action="store_true",
        help=(
            "Run the complete daily publishing pipeline: "
            "sync domains, publish one pending article, "
            "rebuild internal links and SEO files."
        ),
    )

    args = parser.parse_args()

    print()
    print(
        "DomanID - Unified Site Build Pipeline"
    )
    print("Phase 1I")
    print("=" * 68)

    started = time.perf_counter()

    stages = list(
        PIPELINE
    )

    if args.daily:
        blog_stage = (
            "Daily article publisher",
            [
                "blog_generator.py",
            ],
        )

        article_link_index = next(
            index
            for index, stage in enumerate(stages)
            if stage[0] == "Article-domain links"
        )

        stages.insert(
            article_link_index,
            blog_stage,
        )

        print(
            "[MODE] DAILY publishing pipeline enabled."
        )

    if args.skip_fetch:
        stages = [
            stage
            for stage in stages
            if stage[0]
            != "Domain inventory"
        ]

        print(
            "[MODE] Existing domains.json "
            "will be used."
        )

    else:
        print(
            "[MODE] Domain inventory will be "
            "refreshed from Google Sheets."
        )

    print(
        f"[INFO] Pipeline stages: "
        f"{len(stages)}"
    )

    timings: list[
        tuple[str, float]
    ] = []

    for index, (
        title,
        command,
    ) in enumerate(
        stages,
        start=1,
    ):
        elapsed = run_stage(
            index,
            len(stages),
            title,
            command,
        )

        timings.append(
            (
                title,
                elapsed,
            )
        )

    report = validate_build()

    total_elapsed = (
        time.perf_counter()
        - started
    )

    print()
    print("=" * 68)
    print(
        "DomanID BUILD COMPLETE"
    )
    print("=" * 68)

    for title, elapsed in timings:
        print(
            f"{title:<24} "
            f"{elapsed:>7.2f}s"
        )

    print("-" * 68)

    print(
        f"{'Total build time':<24} "
        f"{total_elapsed:>7.2f}s"
    )

    print()
    print(
        f"Domains : "
        f"{report['active_domains']}"
    )

    print(
        f"Articles: "
        f"{report['articles']}"
    )

    print()
    print(
        "[PASS] DomanID site is internally "
        "consistent and ready for local review."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

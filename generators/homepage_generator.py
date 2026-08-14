"""
DomanID - Static Homepage Generator
Phase 1F

Purpose:
- Read normalized domain inventory from data/domains.json.
- Inject Featured Domains directly into index.html.
- Inject All Domains directly into index.html.
- Link each domain card to its internal DomanID domain page.
- Keep the existing homepage design and sections.

Run from project root:

    python generators/homepage_generator.py
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from typing import Any


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = PROJECT_ROOT / "data" / "domains.json"
INDEX_FILE = PROJECT_ROOT / "index.html"
TEMPLATE_FILE = PROJECT_ROOT / "templates" / "index_template.html"


# ============================================================
# HELPERS
# ============================================================


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )


def esc(value: Any) -> str:
    return html.escape(
        clean_text(value),
        quote=True,
    )


def load_domains() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Missing domain data file: {DATA_FILE}"
        )

    with DATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    domains = payload.get("domains")

    if not isinstance(domains, list):
        raise RuntimeError(
            "Invalid domains.json: missing domains list."
        )

    return [
        domain
        for domain in domains
        if clean_text(
            domain.get("status", "")
        ).lower() == "active"
    ]


# ============================================================
# DOMAIN CARDS
# ============================================================


def render_domain_card(
    domain: dict[str, Any],
    *,
    featured: bool,
) -> str:

    title = clean_text(
        domain.get("title")
        or domain.get("domain")
    )

    description = clean_text(
        domain.get("description")
    ) or "A premium digital asset."

    slug = clean_text(
        domain.get("slug")
    )

    internal_url = (
        f"domains/{slug}/"
    )

    premium_badge = ""

    if featured:
        premium_badge = (
            '<span class="premium-badge">'
            'Premium'
            '</span>'
        )

    card_class = (
        "domain-card glass-panel premium-card"
        if featured
        else "domain-card glass-panel"
    )

    domain_type = (
        "premium"
        if featured
        else "standard"
    )

    category = (
        "Premium Domain"
        if featured
        else "Domain"
    )

    return f"""
                <article
                    class="{card_class}"
                    itemscope
                    itemtype="https://schema.org/Product"
                    data-domain="{esc(title.lower())}"
                    data-description="{esc(description.lower())}"
                    data-featured="{'true' if featured else 'false'}"
                >
                    <div class="domain-card-top">
                        <h3
                            class="domain-name"
                            itemprop="name"
                        >
                            <a href="{esc(internal_url)}">
                                {esc(title)}
                            </a>
                        </h3>

                        {premium_badge}
                    </div>

                    <meta
                        itemprop="category"
                        content="{category}"
                    >

                    <p
                        class="domain-card-description"
                        itemprop="description"
                    >
                        {esc(description)}
                    </p>

                    <a
                        href="{esc(internal_url)}"
                        class="btn-glow domain-card-cta"
                        itemprop="url"
                        data-domain-click="{esc(title)}"
                        data-domain-type="{domain_type}"
                    >
                        View Domain
                    </a>

                    <link
                        itemprop="availability"
                        href="https://schema.org/InStock"
                    >
                </article>
""".rstrip()



def render_cards(
    domains: list[dict[str, Any]],
    *,
    featured: bool,
) -> str:

    if not domains:
        return """
                <p
                    style="
                        text-align: center;
                        grid-column: 1 / -1;
                        color: var(--text-muted);
                    "
                >
                    No domains are currently available.
                </p>
""".rstrip()

    return "\n".join(
        render_domain_card(
            domain,
            featured=featured,
        )
        for domain in domains
    )


# ============================================================
# HTML INJECTION
# ============================================================


def replace_element_contents(
    source: str,
    element_id: str,
    content: str,
) -> str:
    """
    Replace the contents of an element identified by id.

    Supports:
        <div ... id="premiumGrid">...</div>

    The grid elements themselves are preserved.
    """

    pattern = re.compile(
        rf'(<div\b[^>]*\bid=["\']{re.escape(element_id)}["\'][^>]*>)'
        rf'.*?'
        rf'(</div>)',
        re.IGNORECASE | re.DOTALL,
    )

    replacement = (
        rf"\1\n{content}\n            \2"
    )

    new_source, count = pattern.subn(
        replacement,
        source,
        count=1,
    )

    if count != 1:
        raise RuntimeError(
            f"Could not locate #{element_id} "
            "in index.html"
        )

    return new_source


def remove_premium_loader(
    source: str,
) -> str:
    """
    Remove the old dynamic Premium loader completely.
    """

    source = re.sub(
        r'<div\s+class=["\']loader["\']\s+id=["\']premiumLoader["\'][^>]*>'
        r'.*?</div>\s*Loading\.\.\.\s*</div>',
        '',
        source,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Safety cleanup in case a previous generation already
    # removed part of the loader but left the text behind.
    source = re.sub(
        r'^\s*Loading\.\.\.\s*$',
        '',
        source,
        count=1,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    return source


# ============================================================
# GENERATION
# ============================================================


def generate_homepage() -> tuple[int, int]:

    domains = load_domains()

    featured_domains = [
        domain
        for domain in domains
        if bool(domain.get("featured"))
    ]

    all_domains = domains

    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(
            f"Missing homepage template: {TEMPLATE_FILE}"
        )

    source = TEMPLATE_FILE.read_text(
        encoding="utf-8"
    )

    premium_html = render_cards(
        featured_domains,
        featured=True,
    )

    source = replace_element_contents(
        source,
        "premiumGrid",
        premium_html,
    )

    source = remove_premium_loader(
        source
    )

    # Normalize generated HTML formatting.
    # Remove trailing whitespace while preserving
    # exactly one final newline.
    source = "\n".join(
        line.rstrip()
        for line in source.splitlines()
    ) + "\n"

    temporary_file = INDEX_FILE.with_suffix(
        ".html.tmp"
    )

    temporary_file.write_text(
        source,
        encoding="utf-8",
        newline="\n",
    )

    temporary_file.replace(
        INDEX_FILE
    )

    return (
        len(featured_domains),
        len(all_domains),
    )


# ============================================================
# MAIN
# ============================================================


def main() -> int:

    print()
    print(
        "DomanID - Static Homepage Generator"
    )
    print("Phase 1F")
    print("-" * 60)

    try:
        featured_count, total_count = (
            generate_homepage()
        )

        print()
        print("=" * 60)
        print("Homepage Generation Report")
        print("=" * 60)

        print(
            f"Featured domains : "
            f"{featured_count}"
        )

        print(
            f"All domains      : "
            f"{total_count}"
        )

        print(
            f"Output           : "
            f"{INDEX_FILE}"
        )

        print("=" * 60)

        print()
        print(
            "[PASS] Static homepage domain "
            "content generated successfully."
        )

        return 0

    except Exception as exc:

        print()
        print(
            "[ERROR] Homepage generation failed: "
            f"{exc}"
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())
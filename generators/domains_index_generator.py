"""
DomanID - Full Domain Inventory Page Generator

Generates:
    domains/index.html

Source of truth:
    data/domains.json
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "domains.json"
)

TEMPLATE_FILE = (
    PROJECT_ROOT
    / "templates"
    / "domains_index_template.html"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "domains"
    / "index.html"
)


def esc(value: Any) -> str:
    return html.escape(
        str(value or ""),
        quote=True,
    )


def load_domains() -> list[dict[str, Any]]:
    payload = json.loads(
        DATA_FILE.read_text(
            encoding="utf-8"
        )
    )

    domains = payload.get(
        "domains",
        [],
    )

    return [
        domain
        for domain in domains
        if str(
            domain.get(
                "status",
                "active",
            )
        ).strip().lower()
        == "active"
    ]


def load_sold_domains() -> list[dict[str, Any]]:
    """
    Load sold domains separately from the authoritative
    domain inventory.

    Sold domains are display-only and must never be mixed
    with the active domain marketplace inventory.
    """
    payload = json.loads(
        DATA_FILE.read_text(
            encoding="utf-8"
        )
    )

    domains = payload.get(
        "domains",
        [],
    )

    return [
        domain
        for domain in domains
        if str(
            domain.get(
                "status",
                "",
            )
        ).strip().lower()
        == "sold"
    ]


def render_card(
    domain: dict[str, Any]
) -> str:

    title = str(
        domain.get("title")
        or domain.get("domain")
        or ""
    ).strip()

    description = str(
        domain.get("description")
        or "A premium digital asset."
    ).strip()

    slug = str(
        domain.get("slug")
        or ""
    ).strip()

    featured = bool(
        domain.get("featured")
    )

    if not title:
        raise ValueError(
            "Domain record is missing a title."
        )

    if not slug:
        raise ValueError(
            f"Domain record is missing slug: {title}"
        )

    badge = ""

    if featured:
        badge = (
            '\n'
            '                    <span '
            'class="inventory-premium-badge">\n'
            '                        Premium\n'
            '                    </span>\n'
        )

    search_text = (
        f"{title} {description}"
    ).lower()

    card_class = (
        "inventory-card "
        "inventory-card-premium"
        if featured
        else "inventory-card"
    )

    return f"""                <article
                    class="{card_class}"
                    data-search="{esc(search_text)}"
                    itemscope
                    itemtype="https://schema.org/Product"
                >
                    <div class="inventory-card-top">

                        <h2 itemprop="name">
                            <a href="{esc(slug)}/">
                                {esc(title)}
                            </a>
                        </h2>
{badge}
                    </div>

                    <p itemprop="description">
                        {esc(description)}
                    </p>

                    <a
                        class="inventory-card-button"
                        href="{esc(slug)}/"
                        itemprop="url"
                    >
                        View Domain
                    </a>

                    <link
                        itemprop="availability"
                        href="https://schema.org/InStock"
                    >
                </article>"""


def render_sold_card(
    domain: dict[str, Any]
) -> str:
    """
    Render a sold domain as a display-only card.

    Sold cards intentionally contain:
    - no domain-page link
    - no purchase link
    - no View Domain button
    - no InStock structured data
    """
    title = str(
        domain.get("title")
        or domain.get("domain")
        or ""
    ).strip()

    description = str(
        domain.get("description")
        or "Previously sold through DomanID."
    ).strip()

    if not title:
        raise ValueError(
            "Sold domain record is missing a title."
        )

    search_text = (
        f"{title} {description}"
    ).lower()

    return f"""                <article
                    class="inventory-card inventory-card-sold"
                    data-search="{esc(search_text)}"
                >
                    <div class="inventory-card-top">

                        <h2>
                            {esc(title)}
                        </h2>

                        <span class="inventory-sold-badge">
                            Sold
                        </span>

                    </div>

                    <p>
                        {esc(description)}
                    </p>

                    <span class="inventory-sold-status">
                        Sold Domain
                    </span>
                </article>"""


def main() -> int:

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Missing domain data: {DATA_FILE}"
        )

    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(
            f"Missing template: {TEMPLATE_FILE}"
        )

    domains = load_domains()
    sold_domains = load_sold_domains()

    if not domains:
        raise RuntimeError(
            "No active domains found."
        )

    cards = "\n\n".join(
        render_card(domain)
        for domain in domains
    )

    sold_cards = "\n\n".join(
        render_sold_card(domain)
        for domain in sold_domains
    )

    source = TEMPLATE_FILE.read_text(
        encoding="utf-8"
    )

    if "{{DOMAIN_COUNT}}" not in source:
        raise RuntimeError(
            "DOMAIN_COUNT placeholder missing "
            "from inventory template."
        )

    if "{{DOMAIN_CARDS}}" not in source:
        raise RuntimeError(
            "DOMAIN_CARDS placeholder missing "
            "from inventory template."
        )

    if "{{SOLD_DOMAIN_CARDS}}" not in source:
        raise RuntimeError(
            "SOLD_DOMAIN_CARDS placeholder missing "
            "from inventory template."
        )

    source = source.replace(
        "{{DOMAIN_COUNT}}",
        str(len(domains)),
    )

    source = source.replace(
        "{{DOMAIN_CARDS}}",
        cards,
    )

    source = source.replace(
        "{{SOLD_DOMAIN_CARDS}}",
        sold_cards,
    )

    source = "\n".join(
        line.rstrip()
        for line in source.splitlines()
    ) + "\n"

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = OUTPUT_FILE.with_suffix(
        ".html.tmp"
    )

    temporary.write_text(
        source,
        encoding="utf-8",
        newline="\n",
    )

    temporary.replace(
        OUTPUT_FILE
    )

    featured_count = sum(
        1
        for domain in domains
        if bool(domain.get("featured"))
    )

    print()
    print(
        "DomanID - Domain Inventory Page Generator"
    )
    print("-" * 60)

    print(
        f"Active domains    : {len(domains)}"
    )

    print(
        f"Premium domains   : {featured_count}"
    )

    print(
        f"Sold domains      : {len(sold_domains)}"
    )

    print(
        f"Output            : {OUTPUT_FILE}"
    )

    print()
    print(
        "[PASS] Full domain inventory page generated."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

"""
DomanID - Static Domain Page Generator
Phase 1C

Purpose:
- Read normalized domain data from data/domains.json.
- Generate one static SEO-friendly HTML page per active domain.
- Remove obsolete generated domain directories safely.
- Keep all generated output local until the phase is approved.

Run from project root:

    python generators/domain_page_generator.py
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "domains.json"
DOMAINS_DIR = PROJECT_ROOT / "domains"

SITE_URL = "https://domanid.com"
SITE_NAME = "DomanID"


# ============================================================
# HELPERS
# ============================================================


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)

    return value


def escape(value: Any) -> str:
    return html.escape(
        clean_text(value),
        quote=True,
    )


def truncate(
    value: str,
    max_length: int,
) -> str:
    value = clean_text(value)

    if len(value) <= max_length:
        return value

    shortened = value[: max_length - 1].rstrip()

    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]

    return shortened.rstrip(".,;:- ") + "…"


def domain_display_name(domain: str) -> str:
    return clean_text(domain)


def build_meta_title(domain: dict[str, Any]) -> str:
    name = domain_display_name(domain["domain"])

    title = (
        f"{name} for Sale | Premium Domain Name | DomanID"
    )

    return truncate(title, 60)


def build_meta_description(
    domain: dict[str, Any],
) -> str:
    name = domain_display_name(domain["domain"])
    description = clean_text(
        domain.get("description", "")
    )

    if description:
        text = (
            f"{name} is available for sale. "
            f"{description}"
        )
    else:
        text = (
            f"{name} is available for sale on DomanID. "
            "Explore this premium domain name for your "
            "business, startup, brand, or online project."
        )

    return truncate(text, 155)


def build_page_intro(
    domain: dict[str, Any],
) -> str:
    description = clean_text(
        domain.get("description", "")
    )

    if description:
        return description

    return (
        "A distinctive domain name available for acquisition "
        "through DomanID."
    )


def infer_domain_category(
    domain: dict[str, Any],
) -> str:
    """
    Infer a practical niche from the domain name and description.

    This is deterministic and local.
    Later Google Sheets may provide an explicit Category column,
    which can override this inference.
    """
    text = (
        f"{domain.get('domain', '')} "
        f"{domain.get('description', '')}"
    ).lower()

    category_keywords = {
        "legal": [
            "lawyer",
            "lawyers",
            "attorney",
            "legal",
            "law firm",
            "accident",
            "discrimination",
        ],
        "travel": [
            "hotel",
            "hotels",
            "travel",
            "vacation",
            "vacations",
            "majorca",
            "tourism",
        ],
        "health": [
            "dental",
            "clinic",
            "nurse",
            "nurses",
            "health",
            "medical",
        ],
        "insurance": [
            "insurance",
            "life insurance",
            "health insurance",
        ],
        "real_estate": [
            "home",
            "house",
            "real estate",
            "property",
            "rental",
        ],
        "automotive": [
            "auto",
            "car",
            "cars",
            "chevrolet",
            "driving",
            "vehicle",
        ],
        "home_services": [
            "pool cleaner",
            "floor",
            "tiling",
            "window tint",
            "furniture",
            "flower shop",
            "flowers",
        ],
        "ecommerce": [
            "store",
            "shop",
            "clothes",
            "deodorant",
            "coins",
            "buy",
        ],
        "finance": [
            "finance",
            "financial",
            "silver",
            "investment",
            "investing",
        ],
        "technology": [
            "digital",
            "tech",
            "software",
            "app",
            "online",
        ],
    }

    scores = {}

    for category, keywords in category_keywords.items():
        score = sum(
            1
            for keyword in keywords
            if keyword in text
        )

        if score:
            scores[category] = score

    if not scores:
        return "general"

    return max(
        scores,
        key=scores.get,
    )


def build_use_cases(
    domain: dict[str, Any],
) -> list[str]:
    category = infer_domain_category(domain)

    cases = {
        "legal": [
            "Law firm or legal services website",
            "Client lead-generation platform",
            "Legal PPC and search campaigns",
            "Specialized legal information portal",
        ],
        "travel": [
            "Travel booking or hotel platform",
            "Destination guide or tourism website",
            "Travel affiliate marketing project",
            "Local travel agency or hospitality brand",
        ],
        "health": [
            "Healthcare clinic or professional practice",
            "Patient information and lead-generation site",
            "Healthcare service marketing campaigns",
            "Specialized medical or wellness platform",
        ],
        "insurance": [
            "Insurance comparison or quote platform",
            "Insurance agency lead-generation website",
            "Paid-search insurance campaigns",
            "Consumer insurance information portal",
        ],
        "real_estate": [
            "Property listing or real-estate website",
            "Local property lead-generation platform",
            "Rental or home services business",
            "Real-estate marketing campaigns",
        ],
        "automotive": [
            "Automotive services or dealership website",
            "Local vehicle lead-generation platform",
            "Auto-related advertising campaigns",
            "Automotive information or service brand",
        ],
        "home_services": [
            "Local home-services business",
            "Service lead-generation website",
            "Local SEO and advertising campaigns",
            "Specialized service company brand",
        ],
        "ecommerce": [
            "Focused e-commerce storefront",
            "Product review or comparison website",
            "Affiliate marketing project",
            "Consumer product brand",
        ],
        "finance": [
            "Financial information platform",
            "Investment-focused content website",
            "Financial lead-generation project",
            "Finance-related digital brand",
        ],
        "technology": [
            "Technology startup or SaaS brand",
            "Digital agency or online platform",
            "Software product or application",
            "Technology marketing campaigns",
        ],
        "general": [
            "Business or startup branding",
            "Marketing and advertising campaigns",
            "Lead-generation or niche website",
            "Long-term digital asset project",
        ],
    }

    return cases[category]


def build_standout_points(
    domain: dict[str, Any],
) -> list[str]:
    category = infer_domain_category(domain)
    name = clean_text(domain.get("domain", ""))

    common = [
        "Recognizable .COM extension",
        "Clear commercial positioning",
    ]

    category_points = {
        "legal": [
            "Strong relevance for legal-service searches",
            "Useful for high-intent client acquisition",
        ],
        "travel": [
            "Clear relevance to travel and hospitality",
            "Suitable for destination-focused marketing",
        ],
        "health": [
            "Clear healthcare service positioning",
            "Suitable for patient acquisition campaigns",
        ],
        "insurance": [
            "Commercial insurance search relevance",
            "Useful for quote and lead-generation funnels",
        ],
        "real_estate": [
            "Strong property-related positioning",
            "Useful for geographically targeted campaigns",
        ],
        "automotive": [
            "Clear automotive-market relevance",
            "Suitable for service and lead-generation campaigns",
        ],
        "home_services": [
            "Strong local-service positioning",
            "Suitable for local SEO and paid advertising",
        ],
        "ecommerce": [
            "Product-focused commercial intent",
            "Suitable for e-commerce and affiliate projects",
        ],
        "finance": [
            "Clear finance or investment positioning",
            "Suitable for financial content and lead generation",
        ],
        "technology": [
            "Flexible digital-brand potential",
            "Suitable for technology products and services",
        ],
        "general": [
            "Flexible brand-development potential",
            "Useful across digital marketing channels",
        ],
    }

    points = category_points[category] + common

    return points[:4]


def find_related_domains(
    domain: dict[str, Any],
    all_domains: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    """
    Find related active domains.

    Priority:
    1. Same inferred category.
    2. Featured domains first.
    3. Alphabetical stability.
    """
    current_name = clean_text(
        domain.get("domain", "")
    )

    current_category = infer_domain_category(
        domain
    )

    candidates = []

    for item in all_domains:
        if clean_text(
            item.get("status", "")
        ).lower() != "active":
            continue

        if clean_text(
            item.get("domain", "")
        ) == current_name:
            continue

        if infer_domain_category(item) != current_category:
            continue

        candidates.append(item)

    candidates.sort(
        key=lambda item: (
            not bool(item.get("featured")),
            clean_text(item.get("domain", "")),
        )
    )

    return candidates[:limit]


def build_about_paragraphs(
    domain: dict[str, Any],
) -> list[str]:
    name = clean_text(domain["domain"])
    category = infer_domain_category(domain)

    introductions = {
        "legal": (
            f"{name} has a clear connection to the legal-services "
            "market and can support a focused identity for firms, "
            "lead-generation businesses, or legal information platforms."
        ),
        "travel": (
            f"{name} has direct relevance to the travel and hospitality "
            "market and can support a booking, tourism, destination, "
            "or travel-marketing project."
        ),
        "health": (
            f"{name} can provide a focused digital identity for a "
            "healthcare practice, patient-acquisition project, medical "
            "service, or specialized health platform."
        ),
        "insurance": (
            f"{name} is positioned for the commercially valuable "
            "insurance sector and may suit agencies, quote platforms, "
            "lead-generation businesses, or consumer information sites."
        ),
        "real_estate": (
            f"{name} can support a property-focused digital presence "
            "for listings, rentals, real-estate services, or geographically "
            "targeted property marketing."
        ),
        "automotive": (
            f"{name} has a clear automotive connection and can support "
            "a dealership, vehicle service, lead-generation platform, "
            "or automotive marketing project."
        ),
        "home_services": (
            f"{name} can provide a clear identity for a specialized "
            "service business and may be particularly useful for local "
            "search visibility and customer acquisition."
        ),
        "ecommerce": (
            f"{name} has commercial potential for an online store, "
            "product-focused brand, review platform, or affiliate "
            "marketing business."
        ),
        "finance": (
            f"{name} can support a finance or investment-focused "
            "platform, content property, lead-generation business, "
            "or specialized financial brand."
        ),
        "technology": (
            f"{name} can support a technology startup, software "
            "product, digital service, agency, or broader online brand."
        ),
        "general": (
            f"{name} is available through DomanID and can provide "
            "a focused digital identity for a business, startup, "
            "online service, or marketing project."
        ),
    }

    second = (
        "A well-matched domain can improve brand recall, make marketing "
        "messages easier to communicate, and provide a dedicated address "
        "for search, advertising, social media, and direct navigation."
    )

    return [
        introductions[category],
        second,
    ]


# ============================================================
# DATA
# ============================================================


def load_domains() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Missing data file: {DATA_FILE}"
        )

    with DATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    domains = payload.get("domains")

    if not isinstance(domains, list):
        raise RuntimeError(
            "domains.json does not contain a valid "
            "'domains' list."
        )

    return domains


# ============================================================
# HTML
# ============================================================


def render_domain_page(
    domain: dict[str, Any],
    all_domains: list[dict[str, Any]],
) -> str:
    name = clean_text(domain["domain"])
    slug = clean_text(domain["slug"])
    description = build_page_intro(domain)

    meta_title = build_meta_title(domain)
    meta_description = build_meta_description(domain)

    canonical = f"{SITE_URL}/domains/{slug}/"

    sale_link = clean_text(
        domain.get("link", "")
    )

    featured = bool(
        domain.get("featured", False)
    )

    badge_html = ""

    if featured:
        badge_html = (
            '<span class="domain-badge">'
            'Featured Domain'
            '</span>'
        )

    use_cases_html = "\n".join(
        f"""
        <div class="value-card glass-panel">
            <span class="value-check">&#10003;</span>
            <span>{escape(item)}</span>
        </div>
        """
        for item in build_use_cases(domain)
    )

    about_paragraphs = build_about_paragraphs(domain)

    about_html = "\n".join(
        f"<p>{escape(paragraph)}</p>"
        for paragraph in about_paragraphs
    )

    standout_html = "\n".join(
        f"<li>{escape(point)}</li>"
        for point in build_standout_points(domain)
    )

    related_domains = find_related_domains(
        domain,
        all_domains,
        limit=3,
    )

    related_cards_html = "\n".join(
        f"""
        <a
            class="related-domain-card glass-panel"
            href="../{escape(item['slug'])}/"
        >
            <strong>
                {escape(item['domain'])}
            </strong>

            <span>
                View domain
            </span>
        </a>
        """
        for item in related_domains
    )


    buy_button = ""

    if sale_link:
        buy_button = f"""
        <a
            class="domain-cta"
            href="{escape(sale_link)}"
            target="_blank"
            rel="noopener noreferrer sponsored"
        >
            View Domain Listing
        </a>
        """

    structured_data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Product",
                "@id": f"{canonical}#domain",
                "name": name,
                "description": meta_description,
                "url": canonical,
                "brand": {
                    "@type": "Brand",
                    "name": SITE_NAME,
                },
                "offers": {
                    "@type": "Offer",
                    "url": sale_link or canonical,
                    "availability": (
                        "https://schema.org/InStock"
                    ),
                    "itemCondition": (
                        "https://schema.org/NewCondition"
                    ),
                },
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{canonical}#breadcrumb",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Home",
                        "item": f"{SITE_URL}/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Domains",
                        "item": f"{SITE_URL}/domains/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": name,
                        "item": canonical,
                    },
                ],
            },
        ],
    }

    structured_json = json.dumps(
        structured_data,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>{escape(meta_title)}</title>

    <meta
        name="description"
        content="{escape(meta_description)}"
    >

    <meta
        name="robots"
        content="index, follow"
    >

    <link
        rel="canonical"
        href="{escape(canonical)}"
    >

    <meta
        property="og:type"
        content="website"
    >

    <meta
        property="og:site_name"
        content="{SITE_NAME}"
    >

    <meta
        property="og:title"
        content="{escape(meta_title)}"
    >

    <meta
        property="og:description"
        content="{escape(meta_description)}"
    >

    <meta
        property="og:url"
        content="{escape(canonical)}"
    >

    <meta
        name="twitter:card"
        content="summary"
    >

    <meta
        name="twitter:title"
        content="{escape(meta_title)}"
    >

    <meta
        name="twitter:description"
        content="{escape(meta_description)}"
    >

    <script type="application/ld+json">
{structured_json}
    </script>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

    <link
        href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@500;600;700;800&display=swap"
        rel="stylesheet"
    >

    <link
        rel="stylesheet"
        href="../../style.css?v=12"
    >

</head>

<body>

    <div class="bg-mesh"></div>

    <header class="site-header">
        <nav
            class="navbar"
            aria-label="Main navigation"
        >
            <div class="container nav-container">

                <a
                    class="brand"
                    href="../../"
                    aria-label="DomanID home"
                >
                    <span class="brand-name">
                        Doman<span class="brand-accent">ID</span>
                    </span>

                    <span class="brand-tagline">
                        Premium Domains
                    </span>
                </a>

                <button
                    class="menu-toggle"
                    id="mobile-menu"
                    type="button"
                    aria-label="Open navigation menu"
                    aria-expanded="false"
                >
                    <span class="bar"></span>
                    <span class="bar"></span>
                    <span class="bar"></span>
                </button>

                <ul class="nav-links">

                    <li><a href="../../index.html">Home</a></li>
                    <li>
                        <a href="../../domains/">
                            Domains
                        </a>
                    </li>
                    <li><a href="../../index.html">Tools</a></li>

                    <li>
                        <a href="../../articles/index.html">
                            Blog
                        </a>
                    </li>

                    <li>
                        <a href="../../about.html">
                            About
                        </a>
                    </li>

                    <li>
                        <a href="../../contact.html">
                            Contact
                        </a>
                    </li>

                    <li class="nav-cta-item">
                        <a
                            class="nav-cta"
                            href="../../#premium"
                        >
                            Premium Picks
                        </a>
                    </li>

                </ul>

            </div>
        </nav>
    </header>

    <main class="domain-detail-main">

        <div class="domain-breadcrumb">
            <a href="../../">Home</a>
            &nbsp;/&nbsp;
            <a href="../../domains/">Domains</a>
            &nbsp;/&nbsp;
            {escape(name)}
        </div>

        <section class="domain-sale-hero">

            {badge_html}

            <div class="domain-sale-label">
                Premium .COM Domain for Sale
            </div>

            <h1 class="domain-name">
                {escape(name)}
            </h1>

            <p class="domain-description">
                {escape(description)}
            </p>

            {buy_button}

        </section>

        <div class="domain-content">

            <section class="domain-content-section">

                <h2>
                    Why {escape(name)}?
                </h2>

                {about_html}

            </section>

            <section class="domain-content-section">

                <h2>
                    Potential Uses
                </h2>

                <div class="domain-value-grid">
                    {use_cases_html}
                </div>

            </section>

            <section class="domain-content-section">

                <h2>
                    Why This Domain Stands Out
                </h2>

                <div class="standout-panel glass-panel">

                    <ul class="standout-list">
                        {standout_html}
                    </ul>

                </div>

            </section>

            <section class="domain-content-section">

                <h2>
                    Related Domains
                </h2>

                <p>
                    Explore other available domains in a
                    similar market or business category.
                </p>

                <div class="related-domain-grid">
                    {related_cards_html}
                </div>

            </section>

            <section
                class="domain-final-cta glass-panel"
            >

                <h2>
                    Interested in {escape(name)}?
                </h2>

                <p>
                    View the domain listing and acquisition
                    details.
                </p>

                {buy_button}

                <br>

                <a
                    class="domain-back"
                    href="../../domains/"
                >
                    &larr; Browse all domains
                </a>

            </section>

        </div>

    </main>

    <footer class="footer">

        <div class="container footer-layout">

            <div class="footer-brand">

                <a
                    class="footer-logo"
                    href="../../"
                >
                    Doman<span>ID</span>
                </a>

                <p>
                    A curated portfolio of business-ready
                    .com domain names.
                </p>

            </div>

            <nav
                class="footer-nav"
                aria-label="Footer navigation"
            >

                <div class="footer-column">
                    <h2>Portfolio</h2>

                    <a href="../../#premium">
                        Premium Domains
                    </a>

                    <a href="../../domains/">
                        All Domains
                    </a>
                </div>

                <div class="footer-column">
                    <h2>Explore</h2>

                    <a href="../../articles/index.html">
                        Blog
                    </a>

                    <a href="../../about.html">
                        About
                    </a>

                    <a href="../../contact.html">
                        Contact
                    </a>
                </div>

                <div class="footer-column">
                    <h2>Legal</h2>

                    <a href="../../terms.html">
                        Terms of Service
                    </a>

                    <a href="../../privacy.html">
                        Privacy Policy
                    </a>
                </div>

            </nav>

        </div>

        <div class="container footer-bottom">

            <p>
                &copy; 2026 DomanID.
                All rights reserved.
            </p>

            <p>
                Premium .com Domain Portfolio
            </p>

        </div>

    </footer>

    <script src="../../app.js"></script>

</body>
</html>
"""


# ============================================================
# GENERATION
# ============================================================


def generate_domain_page(
    domain: dict[str, Any],
    all_domains: list[dict[str, Any]],
) -> Path:
    slug = clean_text(domain["slug"])

    if not slug:
        raise RuntimeError(
            f"Missing slug for domain: "
            f"{domain.get('domain')}"
        )

    output_dir = DOMAINS_DIR / slug
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = output_dir / "index.html"

    rendered = render_domain_page(
        domain,
        all_domains,
    )

    # Normalize generated HTML before writing.
    # This prevents trailing whitespace from being emitted
    # by dynamic multiline HTML fragments.
    rendered = "\n".join(
        line.rstrip()
        for line in rendered.splitlines()
    ) + "\n"

    output_file.write_text(
        rendered,
        encoding="utf-8",
        newline="\n",
    )

    return output_file


def remove_obsolete_domain_pages(
    active_slugs: set[str],
) -> list[str]:
    """
    Remove generated domain directories that are no longer
    present in the active domain inventory.

    IMPORTANT:
    This only operates inside /domains.
    """
    removed: list[str] = []

    if not DOMAINS_DIR.exists():
        return removed

    for item in DOMAINS_DIR.iterdir():
        if not item.is_dir():
            continue

        if item.name in active_slugs:
            continue

        shutil.rmtree(item)

        removed.append(item.name)

    return removed


# ============================================================
# MAIN
# ============================================================


def main() -> int:
    print()
    print("DomanID - Static Domain Page Generator")
    print("Phase 1C")
    print("-" * 60)

    try:
        domains = load_domains()

        active_domains = [
            domain
            for domain in domains
            if clean_text(
                domain.get("status", "")
            ).lower()
            == "active"
        ]

        if not active_domains:
            print(
                "[ERROR] No active domains found."
            )

            return 1

        active_slugs = {
            clean_text(domain["slug"])
            for domain in active_domains
        }

        DOMAINS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        generated_files: list[Path] = []

        for domain in active_domains:
            output_file = generate_domain_page(
                domain,
                domains,
            )

            generated_files.append(
                output_file
            )

            print(
                f"[GENERATED] "
                f"{domain['domain']} "
                f"-> domains/{domain['slug']}/"
            )

        removed = remove_obsolete_domain_pages(
            active_slugs
        )

        print()
        print("=" * 60)
        print("DomanID Domain Page Report")
        print("=" * 60)
        print(
            f"Active domains    : "
            f"{len(active_domains)}"
        )
        print(
            f"Pages generated   : "
            f"{len(generated_files)}"
        )
        print(
            f"Obsolete removed  : "
            f"{len(removed)}"
        )
        print(
            f"Output directory  : "
            f"{DOMAINS_DIR}"
        )
        print("=" * 60)

        if removed:
            print()
            print("Removed obsolete pages:")

            for slug in removed:
                print(
                    f"  - domains/{slug}/"
                )

        print()
        print(
            "[PASS] Static domain pages generated "
            "successfully."
        )

        return 0

    except Exception as exc:
        print()
        print(
            f"[ERROR] Domain page generation failed: "
            f"{exc}"
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())
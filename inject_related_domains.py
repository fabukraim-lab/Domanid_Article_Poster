from __future__ import annotations

import argparse
import html as html_mod
import json
import re
from pathlib import Path
from typing import Any

from generators.domain_page_generator import infer_domain_category


PROJECT_ROOT = Path(__file__).resolve().parent
ARTICLES_DIR = PROJECT_ROOT / "articles"
DOMAINS_FILE = PROJECT_ROOT / "data" / "domains.json"

START_MARKER = "<!-- DOMANID_RELATED_DOMAINS_START -->"
END_MARKER = "<!-- DOMANID_RELATED_DOMAINS_END -->"

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by",
    "for", "from", "has", "in", "is", "it", "its",
    "of", "on", "or", "that", "the", "this", "to",
    "with", "your", "you", "how", "why", "what",
    "domain", "domains", "com", "website", "online",
    "digital", "business",
}


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )


def tokenize(value: str) -> set[str]:
    words = re.findall(
        r"[a-z0-9]+",
        value.lower(),
    )

    return {
        word
        for word in words
        if len(word) >= 3
        and word not in STOP_WORDS
    }


def load_domains() -> list[dict[str, Any]]:
    if not DOMAINS_FILE.exists():
        raise FileNotFoundError(
            f"Missing domain inventory: {DOMAINS_FILE}"
        )

    payload = json.loads(
        DOMAINS_FILE.read_text(
            encoding="utf-8"
        )
    )

    domains = payload.get("domains", [])

    if not isinstance(domains, list):
        raise RuntimeError(
            "Invalid domains.json: domains must be a list."
        )

    return [
        domain
        for domain in domains
        if clean_text(
            domain.get("status", "")
        ).lower() == "active"
    ]


def extract_article_data(
    html_content: str,
) -> dict[str, str]:

    title_match = re.search(
        r"<title>(.*?)</title>",
        html_content,
        re.I | re.S,
    )

    title = clean_text(
        title_match.group(1)
        if title_match
        else ""
    )

    title = re.sub(
        r"\s*[-|]\s*DomanID.*$",
        "",
        title,
        flags=re.I,
    )

    category_match = re.search(
        r'class=["\']article-meta["\'][^>]*>'
        r'(.*?)</',
        html_content,
        re.I | re.S,
    )

    category = ""

    if category_match:
        category = re.sub(
            r"<[^>]+>",
            " ",
            category_match.group(1),
        )

        category = clean_text(
            category.split("|")[0]
        )

    keywords_match = re.search(
        r'<meta\s+name=["\']keywords["\']\s+'
        r'content=["\']([^"\']+)["\']',
        html_content,
        re.I,
    )

    keywords = clean_text(
        keywords_match.group(1)
        if keywords_match
        else ""
    )

    body_match = re.search(
        r'<div\s+class=["\']article-body["\'][^>]*>'
        r'(.*?)'
        r'</div>',
        html_content,
        re.I | re.S,
    )

    body = ""

    if body_match:
        body = re.sub(
            r"<[^>]+>",
            " ",
            body_match.group(1),
        )

        body = html_mod.unescape(body)
        body = clean_text(body)

    return {
        "title": title,
        "category": category,
        "keywords": keywords,
        "body": body,
    }


def infer_article_category(
    article: dict[str, str],
) -> str:
    pseudo_domain = {
        "domain": article["title"],
        "description": (
            f"{article['category']} "
            f"{article['keywords']} "
            f"{article['body'][:2500]}"
        ),
    }

    return infer_domain_category(
        pseudo_domain
    )


def domain_search_text(
    domain: dict[str, Any],
) -> str:
    return clean_text(
        f"{domain.get('domain', '')} "
        f"{domain.get('description', '')}"
    )


def score_domain(
    domain: dict[str, Any],
    article: dict[str, str],
) -> int:

    domain_tokens = tokenize(
        domain_search_text(domain)
    )

    title_tokens = tokenize(
        article["title"]
    )

    category_tokens = tokenize(
        article["category"]
    )

    keyword_tokens = tokenize(
        article["keywords"]
    )

    body_tokens = tokenize(
        article["body"]
    )

    score = 0

    score += (
        len(domain_tokens & title_tokens)
        * 8
    )

    score += (
        len(domain_tokens & category_tokens)
        * 6
    )

    score += (
        len(domain_tokens & keyword_tokens)
        * 5
    )

    score += (
        len(domain_tokens & body_tokens)
        * 1
    )

    article_category = (
        infer_article_category(article)
    )

    domain_category = (
        infer_domain_category(domain)
    )

    if (
        article_category != "general"
        and article_category == domain_category
    ):
        score += 10

    if bool(domain.get("featured")):
        score += 1

    return score


def find_related_domains(
    article: dict[str, str],
    domains: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:

    scored: list[
        tuple[int, str, dict[str, Any]]
    ] = []

    for domain in domains:
        score = score_domain(
            domain,
            article,
        )

        if score <= 0:
            continue

        scored.append(
            (
                score,
                clean_text(
                    domain.get("domain", "")
                ),
                domain,
            )
        )

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    return [
        domain
        for _, _, domain
        in scored[:limit]
    ]


def render_domain_card(
    domain: dict[str, Any],
) -> str:

    name = clean_text(
        domain.get("domain", "")
    )

    slug = clean_text(
        domain.get("slug", "")
    )

    description = clean_text(
        domain.get("description", "")
    )

    badge = ""

    if bool(domain.get("featured")):
        badge = (
            '<span class="premium-badge">'
            'Premium'
            '</span>'
        )

    return f"""
            <a
                href="../domains/{html_mod.escape(slug)}/"
                class="domain-card-inline"
            >
                <div class="domain-card-header">
                    <span class="domain-name">
                        {html_mod.escape(name)}
                    </span>

                    {badge}
                </div>

                <p class="domain-desc">
                    {html_mod.escape(description)}
                </p>

                <span class="domain-cta">
                    View Domain &rarr;
                </span>
            </a>
""".rstrip()


def render_related_block(
    article: dict[str, str],
    domains: list[dict[str, Any]],
) -> str:

    related = find_related_domains(
        article,
        domains,
        limit=3,
    )

    if not related:
        return ""

    cards = "\n".join(
        render_domain_card(domain)
        for domain in related
    )

    return f"""
{START_MARKER}
        <div class="related-premium-domains">

            <h3>
                Related Domains
            </h3>

            <p class="section-subtitle">
                Available domain names related to this topic
            </p>

            <div class="domains-inline-grid">
{cards}
            </div>

        </div>
{END_MARKER}
""".strip()


def remove_existing_related_block(
    content: str,
) -> str:

    managed_pattern = re.compile(
        re.escape(START_MARKER)
        + r".*?"
        + re.escape(END_MARKER),
        re.S,
    )

    content = managed_pattern.sub(
        "",
        content,
    )

    # Remove blocks generated by the old hard-coded script.
    legacy_pattern = re.compile(
        r'\s*<div\s+class=["\']'
        r'related-premium-domains["\']'
        r'.*?'
        r'(?=<div\s+class=["\']cta-box["\'])',
        re.I | re.S,
    )

    content = legacy_pattern.sub(
        "\n",
        content,
    )

    return content


def insert_related_block(
    content: str,
    block: str,
) -> str:

    if not block:
        return content

    cta_match = re.search(
        r'<div\s+class=["\']cta-box["\']',
        content,
        re.I,
    )

    if cta_match:
        position = cta_match.start()

        return (
            content[:position]
            + block
            + "\n\n            "
            + content[position:]
        )

    footer_match = re.search(
        r"</article>|</main>",
        content,
        re.I,
    )

    if footer_match:
        position = footer_match.start()

        return (
            content[:position]
            + block
            + "\n"
            + content[position:]
        )

    return content


def process_article(
    filepath: Path,
    domains: list[dict[str, Any]],
    dry_run: bool = False,
) -> bool:

    original = filepath.read_text(
        encoding="utf-8",
        errors="replace",
    )

    article = extract_article_data(
        original
    )

    cleaned = remove_existing_related_block(
        original
    )

    block = render_related_block(
        article,
        domains,
    )

    # True idempotency:
    # if the currently generated managed block is already
    # present exactly as expected, do not rewrite the file.
    if (
        block
        and START_MARKER in original
        and END_MARKER in original
        and block in original
    ):
        return False

    updated = insert_related_block(
        cleaned,
        block,
    )

    if updated == original:
        return False

    if not dry_run:
        filepath.write_text(
            updated,
            encoding="utf-8",
            newline="\n",
        )

    return True


def main() -> int:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Calculate changes without writing article files."
        ),
    )

    args = parser.parse_args()

    print()
    print(
        "DomanID - Dynamic Article Domain Linker"
    )
    print("Phase 1H")
    print("-" * 60)

    domains = load_domains()

    print(
        f"[INFO] Active domains: {len(domains)}"
    )

    article_files = sorted(
        path
        for path in ARTICLES_DIR.glob("*.html")
        if path.name.lower() != "index.html"
    )

    print(
        f"[INFO] Articles found: {len(article_files)}"
    )

    changed = 0

    for filepath in article_files:

        if process_article(
            filepath,
            domains,
            dry_run=args.dry_run,
        ):
            changed += 1

            prefix = (
                "[WOULD UPDATE]"
                if args.dry_run
                else "[UPDATED]"
            )

            print(
                f"{prefix} {filepath.name}"
            )

    print()
    print("=" * 60)
    print(
        f"Articles processed : {len(article_files)}"
    )
    print(
        f"Articles changed   : {changed}"
    )
    print(
        f"Dry run            : {args.dry_run}"
    )
    print("=" * 60)

    if args.dry_run:
        print(
            "[PASS] Dry-run completed. No files changed."
        )
    else:
        print(
            "[PASS] Dynamic article-domain linking completed."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

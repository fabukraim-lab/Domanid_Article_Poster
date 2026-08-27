"""
DomanID - Domain Data Loader
Phase 1A/1B: Domain Data Foundation

Purpose:
- Read the current domain inventory from Available Domains / Sheet1.
- Normalize all domain records into one consistent structure.
- Preserve active, sold, and expired domain records.
- Detect premium domains.
- Clean normal URLs and Markdown-formatted URLs.
- Generate data/domains.json for local development and later static generation.

This script DOES NOT:
- Modify Google Sheets.
- Modify index.html.
- Modify app.js.
- Generate domain pages yet.
- Publish anything to GitHub.

Run from the project root:

    python generators/domain_data_loader.py
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "domains.json"


# ============================================================
# CURRENT GOOGLE SHEETS SOURCE
# ============================================================

DEFAULT_AVAILABLE_DOMAINS_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vSqCdsEOjGGzEH5vKY7f_TMdobdDNYNcM24d9GDjGyrxZfHR4"
    "lomIuJUc6GzZLQ27OeQst-WYpIC0h1/pub?output=csv"
)

# DOMANID_ALL_DOMAINS_CSV_URL remains as a compatibility
# fallback for existing local or deployment configuration.
AVAILABLE_DOMAINS_CSV_URL = os.getenv(
    "DOMANID_AVAILABLE_DOMAINS_CSV_URL",
    os.getenv(
        "DOMANID_ALL_DOMAINS_CSV_URL",
        DEFAULT_AVAILABLE_DOMAINS_CSV_URL,
    ),
)


# ============================================================
# NETWORK SETTINGS
# ============================================================

REQUEST_TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; DomanIDDomainLoader/1.0; +https://domanid.com)"
)


# ============================================================
# HELPERS
# ============================================================


def clean_text(value: Any) -> str:
    """
    Convert a value to a clean string.
    """
    if value is None:
        return ""

    value = str(value).strip()

    value = re.sub(r"[ \t]+", " ", value)

    return value


def normalize_domain_name(value: str) -> str:
    """
    Normalize a domain name for comparison.

    Examples:
        Example.COM   -> example.com
        https://x.com -> x.com
    """
    value = clean_text(value).lower()

    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"^www\.", "", value)

    value = value.split("/")[0]
    value = value.strip()

    return value


def make_slug(domain: str) -> str:
    """
    Convert a domain name into a filesystem/URL-safe slug.

    Examples:
        Example.com   -> example-com
        my-domain.ai  -> my-domain-ai
    """
    value = normalize_domain_name(domain)

    value = value.replace(".", "-")

    value = re.sub(r"[^a-z0-9-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)

    return value.strip("-")


def extract_markdown_url(value: str) -> str:
    """
    Extract a URL from Markdown link syntax.

    Example:
        [https://example.com](https://example.com)
        ->
        https://example.com
    """
    value = clean_text(value)

    if not value:
        return ""

    match = re.fullmatch(
        r"\[[^\]]*\]\((https?://[^)]+)\)",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        return clean_text(match.group(1))

    return value


def extract_hyperlink_formula(value: str) -> str:
    """
    Support a Google Sheets / Excel HYPERLINK-style formula
    if one ever reaches the CSV data.

    Examples:
        =HYPERLINK("https://example.com","example.com")
        ->
        https://example.com
    """
    value = clean_text(value)

    if not value:
        return ""

    match = re.match(
        r'^=HYPERLINK\(\s*"([^"]+)"',
        value,
        flags=re.IGNORECASE,
    )

    if match:
        return clean_text(match.group(1))

    return value


def normalize_link(value: str) -> str:
    """
    Normalize normal URLs and Markdown-formatted links.
    """
    value = clean_text(value)

    if not value or value == "#":
        return ""

    # Markdown:
    # [https://example.com](https://example.com)
    match = re.fullmatch(
        r"\[[^\]]*\]\((https?://[^)]+)\)",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        value = match.group(1).strip()

    if value.startswith(("http://", "https://")):
        return value

    if value.startswith("www."):
        return f"https://{value}"

    return f"https://{value}"


def normalize_integer_metric(value: Any) -> int | None:
    """
    Normalize an optional whole-number metric.

    Examples:
        "18,100" -> 18100
        "18100"  -> 18100
        ""       -> None

    Raises ValueError for non-numeric input.
    """
    value = clean_text(value)

    if not value:
        return None

    normalized = value.replace(",", "").strip()

    if not re.fullmatch(r"\d+", normalized):
        raise ValueError(
            f"Invalid integer metric: {value!r}"
        )

    return int(normalized)


def normalize_decimal_metric(value: Any) -> float | None:
    """
    Normalize an optional decimal/currency metric.

    Examples:
        "$47.20" -> 47.2
        "47.20"  -> 47.2
        ""       -> None

    Raises ValueError for non-numeric input.
    """
    value = clean_text(value)

    if not value:
        return None

    normalized = (
        value
        .replace("$", "")
        .replace(",", "")
        .strip()
    )

    if not re.fullmatch(
        r"\d+(?:\.\d+)?",
        normalized,
    ):
        raise ValueError(
            f"Invalid decimal metric: {value!r}"
        )

    return float(normalized)


def truthy(value: str) -> bool:
    """
    Interpret common spreadsheet truthy values.
    """
    value = clean_text(value).lower()

    return value in {
        "1",
        "true",
        "yes",
        "y",
        "featured",
        "premium",
        "active",
    }


# ============================================================
# CSV FETCHING
# ============================================================


def fetch_csv(url: str, label: str) -> str:
    """
    Download a published Google Sheets CSV file.
    """
    print(f"[INFO] Fetching {label}...")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/csv,text/plain,*/*",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            raw = response.read()

    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"HTTP error while fetching {label}: "
            f"{exc.code} {exc.reason}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Network error while fetching {label}: "
            f"{exc.reason}"
        ) from exc

    except TimeoutError as exc:
        raise RuntimeError(
            f"Timeout while fetching {label}."
        ) from exc

    text = raw.decode("utf-8-sig")

    if not text.strip():
        raise RuntimeError(
            f"{label} returned an empty CSV."
        )

    return text


def parse_csv(csv_text: str) -> list[dict[str, str]]:
    """
    Parse CSV using Python's standard CSV parser.
    """
    stream = io.StringIO(csv_text)

    reader = csv.DictReader(stream)

    if not reader.fieldnames:
        return []

    rows: list[dict[str, str]] = []

    for raw_row in reader:
        row: dict[str, str] = {}

        for key, value in raw_row.items():
            if key is None:
                continue

            clean_key = clean_text(key)

            if not clean_key:
                continue

            row[clean_key] = clean_text(value)

        if any(row.values()):
            rows.append(row)

    return rows


# ============================================================
# COLUMN ACCESS
# ============================================================


def get_column(
    row: dict[str, str],
    *possible_names: str,
) -> str:
    """
    Read a column case-insensitively.
    """
    normalized = {
        clean_text(key).lower(): value
        for key, value in row.items()
    }

    for name in possible_names:
        value = normalized.get(name.lower())

        if value is not None:
            return clean_text(value)

    return ""


# ============================================================
# DOMAIN NORMALIZATION
# ============================================================


def normalize_domain_record(
    row: dict[str, str],
) -> dict[str, Any] | None:
    """
    Convert one available Google Sheets row into the
    DomanID domain model.

    Preserve every valid domain from Sheet1 and assign
    its inventory state from Expired / Sold.

    Status precedence:
    1. Sold=yes    -> sold
    2. Expired=yes -> expired
    3. Otherwise   -> active

    Premium is stored independently but is used by the site
    only for active domains.
    """
    title = get_column(
        row,
        "Title",
    )

    if not title:
        return None

    domain_key = normalize_domain_name(title)

    if not domain_key:
        return None

    is_expired = truthy(
        get_column(
            row,
            "Expired",
        )
    )

    is_sold = truthy(
        get_column(
            row,
            "Sold",
        )
    )

    if is_sold:
        status = "sold"
    elif is_expired:
        status = "expired"
    else:
        status = "active"

    description = get_column(
        row,
        "Description",
    )

    link = normalize_link(
        get_column(
            row,
            "Link",
        )
    )

    is_premium = truthy(
        get_column(
            row,
            "Premium",
        )
    )

    # --------------------------------------------------------
    # D1 - Commercial search metrics
    # --------------------------------------------------------
    #
    # These values are optional and come directly from the
    # authoritative Google Sheets inventory. Missing metrics
    # remain empty rather than being estimated or invented.
    #
    primary_keyword = get_column(
        row,
        "Primary Keyword",
        "PrimaryKeyword",
        "Keyword",
    )

    monthly_searches = normalize_integer_metric(
        get_column(
            row,
            "Monthly Searches",
            "Monthly Search Volume",
            "Search Volume",
        )
    )

    cpc = normalize_decimal_metric(
        get_column(
            row,
            "CPC",
            "CPC USD",
            "Estimated CPC",
        )
    )

    competition = get_column(
        row,
        "Competition",
        "Paid Competition",
    )

    competition_level = get_column(
        row,
        "Competition Level",
        "Paid Competition Level",
    )

    low_top_of_page_bid = normalize_decimal_metric(
        get_column(
            row,
            "Low Top of Page Bid",
            "Low Bid",
            "Low Top Bid",
        )
    )

    high_top_of_page_bid = normalize_decimal_metric(
        get_column(
            row,
            "High Top of Page Bid",
            "High Bid",
            "High Top Bid",
        )
    )

    search_location = get_column(
        row,
        "Search Location",
        "Location",
        "Market",
    )

    metrics_source = get_column(
        row,
        "Metrics Source",
        "Data Source",
    )

    metrics_updated = get_column(
        row,
        "Metrics Updated",
        "Metrics Updated At",
        "Last Updated",
    )

    record: dict[str, Any] = {
        "title": title,
        "domain": domain_key,
        "slug": make_slug(title),
        "description": description,
        "link": link,
        # Keep "featured" for compatibility with existing
        # generators while exposing the new inventory fields.
        "featured": is_premium and status == "active",
        "premium": is_premium,
        "expired": is_expired,
        "sold": is_sold,
        "status": status,

        # D1 commercial search metrics.
        "primary_keyword": primary_keyword,
        "monthly_searches": monthly_searches,
        "cpc": cpc,
        "competition": competition,
        "competition_level": competition_level,
        "low_top_of_page_bid": low_top_of_page_bid,
        "high_top_of_page_bid": high_top_of_page_bid,
        "search_location": search_location,
        "metrics_source": metrics_source,
        "metrics_updated": metrics_updated,
    }

    return record


# ============================================================
# MERGING
# ============================================================


def merge_domain_data(
    rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """
    Create the authoritative domain inventory from Sheet1.

    Rules:
    1. Every valid domain is retained.
    2. Sold=yes assigns status=sold.
    3. Expired=yes assigns status=expired unless already sold.
    4. Otherwise status=active.
    5. Premium=yes marks an active domain as featured.
    6. Duplicate domain names collapse into one record.
    """
    domains: dict[str, dict[str, Any]] = {}

    for row in rows:
        record = normalize_domain_record(row)

        if record is None:
            continue

        key = record["domain"]

        if key in domains:
            print(
                "[WARN] Duplicate domain in Available Domains: "
                f"{record['title']}"
            )

        domains[key] = record

    status_order = {
        "active": 0,
        "sold": 1,
        "expired": 2,
    }

    result = sorted(
        domains.values(),
        key=lambda item: (
            status_order.get(item["status"], 99),
            not item["featured"],
            item["domain"],
        ),
    )

    return result


# ============================================================
# VALIDATION
# ============================================================


def is_valid_http_url(value: str) -> bool:
    """
    Perform a lightweight URL validation.
    """
    if not value:
        return True

    return bool(
        re.match(
            r"^https?://[^\s]+$",
            value,
            flags=re.IGNORECASE,
        )
    )


def validate_domains(
    domains: list[dict[str, Any]],
) -> list[str]:
    """
    Perform integrity checks before writing domains.json.
    """
    errors: list[str] = []

    seen_domains: set[str] = set()
    seen_slugs: set[str] = set()

    for index, domain in enumerate(domains, start=1):
        title = domain.get("title", "")
        domain_name = domain.get("domain", "")
        slug = domain.get("slug", "")
        link = domain.get("link", "")

        if not title:
            errors.append(
                f"Row {index}: missing title."
            )

        if not domain_name:
            errors.append(
                f"Row {index}: missing normalized domain."
            )

        if not slug:
            errors.append(
                f"Row {index}: missing slug."
            )

        if domain_name in seen_domains:
            errors.append(
                f"Duplicate normalized domain: {domain_name}"
            )

        seen_domains.add(domain_name)

        if slug in seen_slugs:
            errors.append(
                f"Duplicate slug: {slug}"
            )

        seen_slugs.add(slug)

        if not is_valid_http_url(link):
            errors.append(
                f"Invalid link for {title}: {link}"
            )

    return errors


# ============================================================
# OUTPUT
# ============================================================


def build_output_payload(
    domains: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build versioned JSON output.
    """
    featured_count = sum(
        1
        for domain in domains
        if domain["featured"]
    )

    return {
        "schema_version": 2,
        "source": "google_sheets",
        "domain_count": len(domains),
        "featured_count": featured_count,
        "domains": domains,
    }


def save_json(payload: dict[str, Any]) -> None:
    """
    Save normalized domain data as UTF-8 JSON.
    """
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = OUTPUT_FILE.with_suffix(".json.tmp")

    with temporary_file.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")

    temporary_file.replace(OUTPUT_FILE)


# ============================================================
# REPORTING
# ============================================================


def print_report(
    domains: list[dict[str, Any]],
) -> None:
    """
    Print a compact local-test report.
    """
    featured = [
        item
        for item in domains
        if item["featured"]
    ]

    regular = [
        item
        for item in domains
        if not item["featured"]
    ]

    links_count = sum(
        1
        for item in domains
        if item["link"]
    )

    print()
    print("=" * 60)
    print("DomanID Domain Data Report")
    print("=" * 60)
    print(f"Total domains     : {len(domains)}")
    print(f"Premium domains   : {len(featured)}")
    print(f"Regular domains   : {len(regular)}")
    print(f"Domains with link : {links_count}")
    print(f"Output file       : {OUTPUT_FILE}")
    print("=" * 60)

    if domains:
        print()
        print("Sample records:")

        for item in domains[:5]:
            marker = (
                "FEATURED"
                if item["featured"]
                else "REGULAR"
            )

            print(
                f"  [{marker}] "
                f"{item['title']} "
                f"-> {item['slug']}"
            )

    print()


# ============================================================
# MAIN
# ============================================================


def main() -> int:
    """
    Generate available domain data from Available Domains /
    Sheet1.
    """
    print()
    print("DomanID - Domain Data Loader")
    print("Phase 1A/1B")
    print("-" * 60)

    try:
        available_csv = fetch_csv(
            AVAILABLE_DOMAINS_CSV_URL,
            "Available Domains / Sheet1",
        )

        rows = parse_csv(available_csv)

        print(
            f"[INFO] Rows read from Available Domains / Sheet1: "
            f"{len(rows)}"
        )

        domains = merge_domain_data(rows)

        excluded_count = len(rows) - len(domains)

        print(
            "[INFO] Rows excluded, invalid, or duplicated: "
            f"{excluded_count}"
        )

        errors = validate_domains(domains)

        if errors:
            print()
            print("[ERROR] Validation failed:")

            for error in errors:
                print(f"  - {error}")

            print()
            print("domains.json was NOT updated.")

            return 1

        if not domains:
            print(
                "[ERROR] No available domains were found."
            )

            print(
                "domains.json was NOT updated."
            )

            return 1

        payload = build_output_payload(domains)

        save_json(payload)

        print_report(domains)

        print(
            "[PASS] Available domain data generated successfully."
        )

        return 0

    except Exception as exc:
        print()
        print(
            f"[ERROR] Domain data generation failed: {exc}"
        )

        print(
            "domains.json was NOT updated."
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())
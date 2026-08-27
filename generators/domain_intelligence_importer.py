"""
DomanID - Domain Intelligence Importer
D1 - Commercial Intelligence Layer

Purpose:
- Import structured JSON produced by DomanID Domain Intelligence.
- Validate AI-derived commercial intelligence.
- Keep AI analysis separate from verified inventory/search metrics.
- Store accepted intelligence in data/domain_intelligence.json.

This tool does NOT:
- Modify Google Sheets.
- Modify data/domains.json.
- Generate domain pages.
- Publish anything.
- Treat AI analysis as verified market data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DOMAINS_FILE = (
    PROJECT_ROOT
    / "data"
    / "domains.json"
)

INTELLIGENCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "domain_intelligence.json"
)


ALLOWED_DOMAIN_TYPES = {
    "Exact Match Keyword Domain",
    "Partial Match Keyword Domain",
    "Geo-Service Domain",
    "Product Domain",
    "Industry Domain",
    "Brandable Domain",
    "Acronym Domain",
    "Generic Domain",
    "Other",
}


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )


def normalize_domain(value: Any) -> str:
    value = clean_text(value).lower()

    value = re.sub(
        r"^https?://",
        "",
        value,
    )

    value = re.sub(
        r"^www\.",
        "",
        value,
    )

    value = value.split("/")[0]

    return value.strip()


def load_inventory() -> dict[str, dict[str, Any]]:
    if not DOMAINS_FILE.exists():
        raise RuntimeError(
            f"Missing inventory: {DOMAINS_FILE}"
        )

    payload = json.loads(
        DOMAINS_FILE.read_text(
            encoding="utf-8",
        )
    )

    domains = payload.get(
        "domains",
        [],
    )

    if not isinstance(domains, list):
        raise RuntimeError(
            "Invalid domains.json structure."
        )

    return {
        normalize_domain(
            item.get("domain")
        ): item
        for item in domains
        if normalize_domain(
            item.get("domain")
        )
    }


def validate_score(
    value: Any,
    label: str,
) -> None:
    if not isinstance(value, dict):
        raise ValueError(
            f"{label} must be an object."
        )

    score = value.get(
        "score"
    )

    reason = clean_text(
        value.get("reason")
    )

    if not isinstance(
        score,
        (int, float),
    ):
        raise ValueError(
            f"{label}.score must be numeric."
        )

    if not 0 <= score <= 100:
        raise ValueError(
            f"{label}.score must be between 0 and 100."
        )

    if not reason:
        raise ValueError(
            f"{label}.reason is required."
        )


def validate_report(
    report: dict[str, Any],
    inventory: dict[str, dict[str, Any]],
) -> str:
    if not isinstance(report, dict):
        raise ValueError(
            "Report must be a JSON object."
        )

    domain = normalize_domain(
        report.get("domain")
    )

    if not domain:
        raise ValueError(
            "Missing domain."
        )

    if domain not in inventory:
        raise ValueError(
            f"Domain is not present in DomanID inventory: "
            f"{domain}"
        )

    classification = report.get(
        "classification"
    )

    if not isinstance(
        classification,
        dict,
    ):
        raise ValueError(
            "Missing classification object."
        )

    domain_type = clean_text(
        classification.get(
            "domain_type"
        )
    )

    if domain_type not in ALLOWED_DOMAIN_TYPES:
        raise ValueError(
            f"Unsupported domain type: {domain_type!r}"
        )

    confidence = classification.get(
        "confidence"
    )

    if not isinstance(
        confidence,
        (int, float),
    ):
        raise ValueError(
            "classification.confidence must be numeric."
        )

    if not 0 <= confidence <= 100:
        raise ValueError(
            "classification.confidence must be between 0 and 100."
        )

    ai_scores = report.get(
        "ai_scores"
    )

    if not isinstance(
        ai_scores,
        dict,
    ):
        raise ValueError(
            "Missing ai_scores object."
        )

    required_scores = {
        "brandability",
        "commercial_strength",
        "memorability",
        "clarity",
        "seo_relevance",
        "ppc_relevance",
        "overall_strength",
    }

    # Support the corrected field first.
    # Older pilot output may still use buyer_demand.
    if "buyer_fit" not in ai_scores:
        if "buyer_demand" in ai_scores:
            ai_scores["buyer_fit"] = (
                ai_scores.pop(
                    "buyer_demand"
                )
            )
        else:
            raise ValueError(
                "Missing AI score: buyer_fit"
            )

    for name in sorted(
        required_scores
        | {"buyer_fit"}
    ):
        if name not in ai_scores:
            raise ValueError(
                f"Missing AI score: {name}"
            )

        validate_score(
            ai_scores[name],
            f"ai_scores.{name}",
        )

    verified = report.get(
        "verified_metrics",
        {},
    )

    if verified is None:
        verified = {}

    if not isinstance(
        verified,
        dict,
    ):
        raise ValueError(
            "verified_metrics must be an object."
        )

    # AI Studio is not permitted to introduce
    # unverified numerical search/PPC metrics.
    source = clean_text(
        verified.get(
            "metrics_source"
        )
    )

    numeric_metric_names = [
        "monthly_searches",
        "cpc",
        "competition",
        "low_top_of_page_bid",
        "high_top_of_page_bid",
        "indicative_paid_search_value",
    ]

    if (
        not source
        or source.lower()
        == "not connected"
    ):
        for name in numeric_metric_names:
            if verified.get(name) is not None:
                raise ValueError(
                    "Unverified numeric metric detected: "
                    f"{name}"
                )

    return domain


def sanitize_report(
    report: dict[str, Any],
) -> dict[str, Any]:
    result = json.loads(
        json.dumps(
            report,
            ensure_ascii=False,
        )
    )

    ai_scores = result.get(
        "ai_scores",
        {},
    )

    if (
        "buyer_fit" not in ai_scores
        and "buyer_demand" in ai_scores
    ):
        ai_scores["buyer_fit"] = (
            ai_scores.pop(
                "buyer_demand"
            )
        )

    # Verified metrics belong to the inventory /
    # verified-data pipeline, not the AI intelligence store.
    result.pop(
        "verified_metrics",
        None,
    )

    result["domain"] = normalize_domain(
        result.get("domain")
    )

    result["intelligence_type"] = (
        "ai_analysis"
    )

    return result


def load_existing() -> dict[str, Any]:
    if not INTELLIGENCE_FILE.exists():
        return {
            "schema_version": 1,
            "source": (
                "domanid_domain_intelligence"
            ),
            "domains": {},
        }

    payload = json.loads(
        INTELLIGENCE_FILE.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(
        payload.get("domains"),
        dict,
    ):
        raise RuntimeError(
            "Invalid domain_intelligence.json structure."
        )

    return payload


def import_report(
    input_file: Path,
    dry_run: bool = True,
) -> int:
    inventory = load_inventory()

    report = json.loads(
        input_file.read_text(
            encoding="utf-8-sig",
        )
    )

    domain = validate_report(
        report,
        inventory,
    )

    sanitized = sanitize_report(
        report
    )

    payload = load_existing()

    existing = payload[
        "domains"
    ].get(domain)

    changed = (
        existing
        != sanitized
    )

    print("=" * 72)
    print("DOMANID DOMAIN INTELLIGENCE IMPORT")
    print("=" * 72)
    print("DOMAIN       :", domain)
    print(
        "IN INVENTORY :",
        domain in inventory,
    )
    print(
        "DOMAIN TYPE  :",
        sanitized
        .get("classification", {})
        .get("domain_type"),
    )
    print(
        "WOULD CHANGE :"
        if dry_run
        else "CHANGED      :",
        changed,
    )
    print("DRY RUN      :", dry_run)

    if dry_run:
        print()
        print(
            "[INFO] Validation passed."
        )
        print(
            "[INFO] No files modified."
        )
        return 0

    payload["domains"][
        domain
    ] = sanitized

    INTELLIGENCE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = (
        INTELLIGENCE_FILE
        .with_suffix(".json.tmp")
    )

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    temporary.replace(
        INTELLIGENCE_FILE
    )

    print()
    print(
        "[PASS] AI intelligence imported."
    )
    print(
        f"[PASS] Updated: {INTELLIGENCE_FILE}"
    )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input",
        type=Path,
        help=(
            "Path to a DomanID AI Studio "
            "analysis JSON file."
        ),
    )

    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Write validated analysis to "
            "data/domain_intelligence.json."
        ),
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(
            f"[ERROR] Input file not found: "
            f"{args.input}"
        )
        return 1

    try:
        return import_report(
            args.input,
            dry_run=not args.write,
        )

    except Exception as exc:
        print()
        print(
            f"[ERROR] Intelligence import failed: "
            f"{exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )

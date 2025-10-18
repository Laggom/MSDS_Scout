#!/usr/bin/env python3
"""Sigma-Aldrich SDS downloader using Playwright MCP helpers."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from sds_common import DownloadRecord, build_summary, normalize_languages, print_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_HELPER = REPO_ROOT / "scripts" / "download_sds_with_playwright.js"


def parse_product_url(product_url: str) -> Optional[Tuple[str, str, str, str]]:
    match = re.match(
        r"https://www\.sigmaaldrich\.com/([A-Z]{2})/([a-z]{2})/product/([^/]+)/([^/?#]+)",
        product_url,
    )
    if not match:
        return None
    return match.group(1), match.group(2), match.group(3), match.group(4)


def ensure_helper_exists() -> None:
    if not DOWNLOAD_HELPER.exists():
        raise FileNotFoundError(
            f"Required helper script is missing: {DOWNLOAD_HELPER.relative_to(REPO_ROOT)}"
        )


def download_with_playwright(
    sds_url: str,
    output_path: Path,
    referer: str,
    accept_language: str,
) -> Optional[DownloadRecord]:
    """Invoke the Node.js helper that uses Playwright request API."""
    command = [
        "node",
        str(DOWNLOAD_HELPER.relative_to(REPO_ROOT)),
        sds_url,
        str(output_path),
        referer,
        accept_language,
    ]

    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=180,
    )

    if result.returncode != 0:
        print(f"  Helper failed with exit code {result.returncode}")
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("  Unable to decode helper response:")
        print(result.stdout.strip())
        return None

    status = payload.get("status")
    headers = payload.get("headers", {})
    content_type = headers.get("content-type", "")

    if status != 200:
        print(f"  Failed: HTTP {status}")
        return None

    if "pdf" not in content_type.lower():
        print(f"  Failed: Content-Type '{content_type}' is not PDF")
        return None

    print(f"  Saved {output_path}")
    return DownloadRecord(
        path=output_path,
        languages=[accept_language.split(",")[0].split("-")[1].lower()],
        source_url=sds_url,
        metadata={"referer": referer},
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Sigma-Aldrich SDS PDFs using Playwright MCP.",
    )
    parser.add_argument(
        "--product-url",
        help="Product page URL (e.g. https://www.sigmaaldrich.com/KR/ko/product/sigald/34873)",
    )
    parser.add_argument(
        "legacy_product_url",
        nargs="?",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",
        default=[],
        help="Language codes to download (e.g. ko en). Defaults to the language encoded in the URL.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="data/sds_aldrich",
        help="Directory for downloaded PDFs (default: data/sds_aldrich).",
    )

    args = parser.parse_args()
    product_url = args.product_url or args.legacy_product_url
    if not product_url:
        parser.error("제품 페이지 URL을 --product-url 옵션으로 지정해주세요.")

    ensure_helper_exists()

    parsed = parse_product_url(product_url)
    if not parsed:
        print(f"Invalid product URL format: {product_url}")
        print("Example: https://www.sigmaaldrich.com/KR/ko/product/sigald/34873")
        return

    country, default_language, brand, product_number = parsed
    languages = normalize_languages(args.languages) or [default_language]
    accept_language = f"{default_language}-{country},{default_language};q=0.9,en-US;q=0.8,en;q=0.7"

    output_root = (REPO_ROOT / args.output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"Product number: {product_number}")
    print(f"Brand: {brand}")
    print(f"Country code: {country}")
    print(f"Requested languages: {', '.join(languages)}")

    records: List[DownloadRecord] = []
    for language in languages:
        sds_url = f"https://www.sigmaaldrich.com/{country}/{language}/sds/{brand}/{product_number}"
        filename = f"{product_number}_{country}_{language.upper()}.pdf"
        output_path = output_root / filename

        print(f"\nAttempting SDS download ({language}): {sds_url}")
        record = download_with_playwright(
            sds_url,
            output_path,
            product_url,
            accept_language,
        )
        if record:
            record.languages = [language.lower()]
            records.append(record)

    summary = build_summary(
        provider="aldrich",
        product_identifier=product_number,
        product_url=product_url,
        downloads=records,
        notes={"brand": brand, "country": country},
    )
    print_summary(summary)

    sys.exit(0 if records else 1)


if __name__ == "__main__":
    main()

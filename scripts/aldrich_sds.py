#!/usr/bin/env python3
"""Sigma-Aldrich SDS downloader using direct HTTP requests."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from pathlib import Path
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup
from curl_cffi import requests
from curl_cffi.requests import RequestsError

from sds_common import DownloadRecord, build_summary, normalize_languages, print_summary

REPO_ROOT = Path(__file__).resolve().parents[1]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

HTML_ACCEPT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
)

PDF_ACCEPT = "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8"


class AldrichClient:
    """A client for downloading SDSs from Sigma-Aldrich."""

    def __init__(self) -> None:
        self.session = requests.Session(impersonate="chrome120")
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": HTML_ACCEPT,
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            }
        )

    def get_product_url_from_search(
        self, search_term: str, country: str, language: str
    ) -> Optional[str]:
        """Search for a product and return the URL of the first result."""
        search_url = f"https://www.sigmaaldrich.com/{country}/{language}/search/{urllib.parse.quote(search_term)}"
        try:
            response = self.session.get(
                search_url,
                params={
                    "focus": "products",
                    "page": "1",
                    "perpage": "30",
                    "sort": "relevance",
                    "term": search_term,
                    "type": "product",
                },
                timeout=60,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            first_result = soup.find("a", attrs={"id": re.compile(r"NAME-pdp-link-.*")})
            if first_result and first_result.has_attr("href"):
                return urllib.parse.urljoin(response.url, first_result["href"])
        except RequestsError as exc:
            print(f"Search failed: {exc}")
        return None

    def prime_session(self, product_url: str, accept_language: str) -> None:
        """Fetch the product page once to obtain cookies and verify access."""
        response = self.session.get(
            product_url,
            timeout=60,
            headers={"Accept-Language": accept_language},
        )
        response.raise_for_status()

    def download_sds(
        self,
        sds_url: str,
        output_path: Path,
        product_url: str,
        country: str,
        language: str,
    ) -> Optional[DownloadRecord]:
        accept_language = f"{language}-{country},{language};q=0.9,en-US;q=0.8,en;q=0.7"
        try:
            response = self.session.get(
                sds_url,
                timeout=90,
                headers={
                    "Accept": PDF_ACCEPT,
                    "Accept-Language": accept_language,
                    "Referer": product_url,
                },
            )
        except RequestsError as exc:
            print(f"  Failed ({language}): {exc}")
            return None

        if response.status_code != 200:
            print(f"  Failed ({language}): HTTP {response.status_code}")
            return None

        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower():
            preview = response.text[:200] if response.text else ""
            print(f"  Failed ({language}): unexpected content-type '{content_type}' ({preview})")
            return None

        output_path.write_bytes(response.content)
        print(f"  Saved {output_path}")

        return DownloadRecord(
            path=output_path,
            languages=[language.lower()],
            source_url=sds_url,
            metadata={
                "referer": product_url,
            },
        )


def parse_product_url(product_url: str) -> Optional[Tuple[str, str, str, str]]:
    match = re.match(
        r"https://www\.sigmaaldrich\.com/([A-Z]{2})/([a-z]{2})/product/([^/]+)/([^/?#]+)",
        product_url,
    )
    if not match:
        return None
    return match.group(1), match.group(2), match.group(3), match.group(4)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Sigma-Aldrich SDS PDFs without Playwright MCP.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--product-url",
        help="Product page URL (e.g. https://www.sigmaaldrich.com/KR/ko/product/sigald/34873)",
    )
    group.add_argument(
        "--search-term",
        help="A search term (e.g., a product name or CAS number).",
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
    client = AldrichClient()

    if args.search_term:
        print(f"Searching for '{args.search_term}'...")
        # Use a default URL to extract country and language
        default_url = "https://www.sigmaaldrich.com/KR/ko/product/sigald/34873"
        parsed_default = parse_product_url(default_url)
        if not parsed_default:
            print("Could not parse default URL.")
            sys.exit(1)
        country, language, _, _ = parsed_default

        product_url = client.get_product_url_from_search(
            args.search_term, country, language
        )
        if not product_url:
            print("Could not find a product URL for the given search term.")
            sys.exit(1)
        print(f"Found product URL: {product_url}")
    else:
        product_url = args.product_url or args.legacy_product_url

    if not product_url:
        parser.error("Please provide a product page URL with --product-url or a search term with --search-term.")

    parsed = parse_product_url(product_url)
    if not parsed:
        print(f"Invalid product URL format: {product_url}")
        print("Example: https://www.sigmaaldrich.com/KR/ko/product/sigald/34873")
        sys.exit(1)

    country, default_language, brand, product_number = parsed
    languages = normalize_languages(args.languages) or [default_language]

    accept_language = f"{default_language}-{country},{default_language};q=0.9,en-US;q=0.8,en;q=0.7"
    try:
        client.prime_session(product_url, accept_language)
    except RequestsError as exc:
        print(f"Failed to fetch product page: {exc}")
        sys.exit(1)

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
        record = client.download_sds(
            sds_url=sds_url,
            output_path=output_path,
            product_url=product_url,
            country=country,
            language=language,
        )
        if record:
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

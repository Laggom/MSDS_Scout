#!/usr/bin/env python3
"""TCI product HTML and SDS downloader using plain HTTP requests."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from curl_cffi import requests
from curl_cffi.requests import RequestsError

from sds_common import DownloadRecord, build_summary, normalize_languages, print_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
URL_DEFAULT = "https://www.tcichemicals.com/KR/ko/p/L0483"
SEARCH_ENDPOINT_TEMPLATE = "https://www.tcichemicals.com/{country}/{language}/search"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

HTML_ACCEPT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
)


def create_session() -> requests.Session:
    session = requests.Session(impersonate="chrome120")
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": HTML_ACCEPT,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }
    )
    return session


def fetch_product_page(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response.text


def resolve_product_url_from_search(
    session: requests.Session,
    *,
    term: str,
    country: str,
    language: str,
) -> Optional[str]:
    if not term.strip():
        return None

    search_url = SEARCH_ENDPOINT_TEMPLATE.format(country=country, language=language)
    params = {"keyword": term}
    response = session.get(search_url, params=params, timeout=60)
    response.raise_for_status()

    match = re.search(r'href="(/[^"]+/p/[^"]+)"', response.text)
    if not match:
        return None

    path = match.group(1)
    return urljoin("https://www.tcichemicals.com", path)


@dataclass
class SDSMetadata:
    product_code: str
    selected_country: str
    languages: List[Tuple[str, str]]
    context_path: str


class SDSMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.product_code: Optional[str] = None
        self.selected_country: Optional[str] = None
        self.context_path: str = "/"
        self.languages: List[Tuple[str, str]] = []
        self._in_lang_selector = False
        self._current_value: Optional[str] = None
        self._current_label: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "input":
            element_id = attrs_dict.get("id")
            value = (attrs_dict.get("value") or "").strip()
            if element_id == "sdsProductCode":
                self.product_code = value
            elif element_id == "selectedCountry":
                self.selected_country = value
        elif tag == "select" and attrs_dict.get("id") == "langSelector":
            self._in_lang_selector = True
        elif self._in_lang_selector and tag == "option":
            self._current_value = (attrs_dict.get("value") or "").strip()
            self._current_label = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "select" and self._in_lang_selector:
            self._in_lang_selector = False
        elif tag == "option" and self._in_lang_selector and self._current_value:
            label = "".join(self._current_label).strip()
            self.languages.append((self._current_value, label))
            self._current_value = None
            self._current_label = []

    def handle_data(self, data: str) -> None:
        if self._in_lang_selector and self._current_value is not None:
            self._current_label.append(data)


def extract_csrf_token(html: str) -> Optional[str]:
    match = re.search(r"ACC\.config\.CSRFToken\s*=\s*'([^']+)'", html)
    return match.group(1) if match else None


def parse_sds_metadata(html: str) -> Optional[SDSMetadata]:
    parser = SDSMetadataParser()
    parser.feed(html)

    if not parser.product_code or not parser.selected_country:
        return None

    context_match = re.search(r"ACC\.config\.encodedContextPath\s*=\s*'([^']+)'", html)
    context_path = "/"
    if context_match:
        context_path = context_match.group(1).replace("\\/", "/") or "/"

    return SDSMetadata(
        product_code=parser.product_code,
        selected_country=parser.selected_country,
        languages=parser.languages,
        context_path=context_path,
    )


def download_sds_documents(
    session: requests.Session,
    product_url: str,
    metadata: SDSMetadata,
    languages: List[str],
    output_dir: Path,
    csrf_token: Optional[str],
) -> List[DownloadRecord]:
    parsed_url = urlparse(product_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    endpoint_path = f"{metadata.context_path.rstrip('/')}/documentSearch/productSDSSearchDoc"
    sds_url = urljoin(base_url, endpoint_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    available_languages: Dict[str, str] = {code: label for code, label in metadata.languages if code}

    records: List[DownloadRecord] = []
    for requested_lang in languages:
        lang = requested_lang.strip()
        if not lang:
            continue
        if available_languages and lang not in available_languages:
            print(f"- Skipping '{lang}': not listed as an available language on the page.")
            continue

        data = {
            "productCode": metadata.product_code.upper(),
            "langSelector": lang,
            "selectedCountry": metadata.selected_country,
        }
        if csrf_token:
            data["CSRFToken"] = csrf_token

        try:
            response = session.post(
                sds_url,
                data=data,
                timeout=60,
                headers={
                    "Referer": product_url,
                    "Origin": base_url,
                    "Accept": "*/*",
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
            )
        except RequestsError as exc:
            print(f"- SDS download failed ({lang}): {exc}")
            continue

        if response.status_code != 200:
            print(f"- SDS download failed ({lang}): HTTP {response.status_code}")
            continue

        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
            response_text = response.headers.get("response-text") or response.text[:200]
            print(f"- SDS download failed ({lang}): {response_text}")
            continue

        filename = None
        disposition = response.headers.get("Content-Disposition", "")
        if disposition:
            match = re.search(r'filename[^;=\n]*=((["\']).*?\2|[^;\n]*)', disposition)
            if match:
                filename = match.group(1).strip("\"'")
        if not filename:
            filename = f"{metadata.product_code}_{lang}.pdf"

        output_path = output_dir / filename
        output_path.write_bytes(response.content)
        print(f"- SDS saved ({lang}): {output_path}")

        records.append(
            DownloadRecord(
                path=output_path,
                languages=normalize_languages([lang]),
                source_url=sds_url,
                metadata={
                    "productCode": metadata.product_code,
                    "country": metadata.selected_country,
                },
            )
        )

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--product-url",
        "--url",
        dest="product_url",
        default=URL_DEFAULT,
        help="TCI product page URL",
    )
    parser.add_argument(
        "--html-output",
        "--output",
        dest="html_output",
        default="tci_product.html",
        help="Path for saving the fetched HTML (optional).",
    )
    parser.add_argument(
        "--download-sds",
        action="store_true",
        help="Download SDS PDFs in addition to saving the HTML.",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        help="Language codes to download (e.g. ko en). Defaults to the languages listed on the page.",
    )
    parser.add_argument(
        "--output-dir",
        dest="sds_output_dir",
        default="data/sds",
        help="Directory for downloaded SDS PDFs.",
    )
    parser.add_argument(
        "--use-existing-session",
        action="store_true",
        help="Deprecated flag kept for compatibility; sessions are handled automatically.",
    )
    parser.add_argument(
        "--search-term",
        help="Lookup the product by material name or CAS number and use the top result."
    )
    args = parser.parse_args()

    product_url = args.product_url
    session = create_session()
    if args.search_term:
        parsed = urlparse(product_url)
        segments = [segment for segment in parsed.path.split("/") if segment]
        country = segments[0] if len(segments) >= 1 else "KR"
        language = segments[1] if len(segments) >= 2 else "ko"
        resolved = resolve_product_url_from_search(
            session,
            term=args.search_term,
            country=country,
            language=language,
        )
        if not resolved:
            print(f"No TCI product found for search term '{args.search_term}'.")
            raise SystemExit(1)
        print(f"Resolved search term '{args.search_term}' to: {resolved}")
        product_url = resolved

    try:
        html = fetch_product_page(session, product_url)
    except RequestsError as exc:
        print(f"Failed to fetch product page: {exc}")
        raise SystemExit(1) from exc

    html_output_path = (REPO_ROOT / args.html_output).resolve()
    html_output_path.write_text(html, encoding="utf-8")
    print(f"HTML saved ({len(html)} bytes): {html_output_path}")

    metadata = parse_sds_metadata(html)
    product_code = metadata.product_code if metadata else urlparse(product_url).path.rstrip("/").split("/")[-1]

    records: List[DownloadRecord] = []
    if args.download_sds:
        if not metadata:
            print("SDS metadata not found in the HTML; cannot download SDS.")
        else:
            csrf_token = extract_csrf_token(html)
            if not csrf_token:
                print("Warning: CSRF token not found; SDS download may fail.")

            requested_languages = normalize_languages(args.languages) or [
                code for code, _ in metadata.languages if code
            ]
            if not requested_languages:
                print("No languages requested; skipping SDS download.")
            else:
                sds_output_dir = (REPO_ROOT / args.sds_output_dir).resolve()
                records = download_sds_documents(
                    session,
                    product_url,
                    metadata,
                    requested_languages,
                    sds_output_dir,
                    csrf_token,
                )
                if not records:
                    print("No SDS files were downloaded.")

    summary = build_summary(
        provider="tci",
        product_identifier=product_code,
        product_url=product_url,
        html_path=html_output_path,
        downloads=records,
        notes={"userAgent": USER_AGENT},
    )
    print_summary(summary)


if __name__ == "__main__":
    main()

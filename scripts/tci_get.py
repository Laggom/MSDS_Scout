#!/usr/bin/env python3
"""Fetch the TCI product page HTML using cookies gathered via Playwright MCP."""

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION_JSON = REPO_ROOT / "data" / "tci_session.json"
URL_DEFAULT = "https://www.tcichemicals.com/KR/ko/p/L0483"


def refresh_session(url: str) -> dict:
    """Invoke the Playwright MCP helper to refresh cookies and headers."""
    result = subprocess.run(
        ["node", "scripts/fetchHeaders.js", url],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
        timeout=120,
    )
    session = json.loads(result.stdout)
    SESSION_JSON.parent.mkdir(parents=True, exist_ok=True)
    SESSION_JSON.write_text(json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8")
    return session


def load_cookies(session: dict) -> dict:
    """Convert Playwright session cookie array into requests-compatible dict."""
    return {cookie["name"]: cookie["value"] for cookie in session.get("cookies", {}).get("cookies", [])}


def build_headers() -> dict:
    """Headers that mirror the Playwright MCP request context defaults."""
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "User-Agent": "Playwright/1.57.0-alpha",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
    }


def create_requests_session(headers: Dict[str, str], cookies: Dict[str, str]) -> requests.Session:
    session = requests.Session()
    session.headers.update(headers)
    session.cookies.update(cookies)
    return session


def fetch_html(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


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
        self.sds_file_path: Optional[str] = None
        self.languages: List[Tuple[str, str]] = []
        self._in_lang_selector = False
        self._current_option_value: Optional[str] = None
        self._current_option_label: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attributes = dict(attrs)
        if tag == "input":
            element_id = attributes.get("id")
            value = (attributes.get("value") or "").strip()
            if element_id == "sdsProductCode":
                self.product_code = value
            elif element_id == "selectedCountry":
                self.selected_country = value
            elif element_id == "sdsFilePath":
                self.sds_file_path = value
        elif tag == "select" and attributes.get("id") == "langSelector":
            self._in_lang_selector = True
        elif self._in_lang_selector and tag == "option":
            self._current_option_value = (attributes.get("value") or "").strip()
            self._current_option_label = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "select" and self._in_lang_selector:
            self._in_lang_selector = False
        elif tag == "option" and self._in_lang_selector and self._current_option_value:
            label = "".join(self._current_option_label).strip()
            self.languages.append((self._current_option_value, label))
            self._current_option_value = None
            self._current_option_label = []

    def handle_data(self, data: str) -> None:
        if self._in_lang_selector and self._current_option_value is not None:
            self._current_option_label.append(data)


def extract_csrf_token(html: str) -> Optional[str]:
    """Extract CSRF token from HTML page."""
    match = re.search(r"ACC\.config\.CSRFToken\s*=\s*'([^']+)'", html)
    return match.group(1) if match else None


def parse_sds_metadata(html: str) -> Optional[SDSMetadata]:
    parser = SDSMetadataParser()
    parser.feed(html)

    if not parser.product_code or not parser.selected_country:
        return None

    context_path = "/"
    match = re.search(r"ACC\.config\.encodedContextPath\s*=\s*'([^']+)'", html)
    if match:
        context_path = match.group(1).replace("\\/", "/") or "/"

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
    csrf_token: Optional[str] = None,
) -> List[Path]:
    parsed_url = urlparse(product_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    endpoint_path = f"{metadata.context_path.rstrip('/')}/documentSearch/productSDSSearchDoc"
    sds_url = urljoin(base_url, endpoint_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    available_languages: Dict[str, str] = {code: label for code, label in metadata.languages if code}

    downloaded_files: List[Path] = []
    for lang_code in languages:
        lang = lang_code.strip()
        if not lang:
            continue
        if available_languages and lang not in available_languages:
            print(f"경고: 페이지에서 찾을 수 없는 언어 코드 '{lang}' 이므로 건너뜁니다.")
            continue

        data = {
            "productCode": metadata.product_code.upper(),
            "langSelector": lang,
            "selectedCountry": metadata.selected_country,
        }

        # Add CSRF token if available
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
        except requests.RequestException as exc:
            print(f"SDS 다운로드 실패({lang}): {exc}")
            continue

        if response.status_code != 200:
            print(f"SDS 다운로드 실패({lang}): HTTP {response.status_code}")
            continue

        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type and "octet-stream" not in content_type:
            response_text = response.headers.get("response-text") or response.text[:200]
            print(f"SDS 다운로드 실패({lang}): {response_text}")
            continue

        disposition = response.headers.get("Content-Disposition", "")
        filename: Optional[str] = None
        if disposition:
            match = re.search(r'filename[^;=\n]*=((["\']).*?\2|[^;\n]*)', disposition)
            if match:
                filename = match.group(1).strip("\"'")

        if not filename:
            suffix = lang
            filename = f"{metadata.product_code}_{suffix}.pdf"

        output_path = output_dir / filename
        output_path.write_bytes(response.content)
        print(f"SDS 저장 ({lang}): {output_path}")
        downloaded_files.append(output_path)

    return downloaded_files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=URL_DEFAULT, help="Product page URL to download")
    parser.add_argument(
        "--output",
        default="tci_product.html",
        help="File path (relative to repo root) to save the HTML response",
    )
    parser.add_argument(
        "--use-existing-session",
        action="store_true",
        help="Skip refreshing cookies with Playwright MCP and reuse data/tci_session.json",
    )
    parser.add_argument(
        "--download-sds",
        action="store_true",
        help="제품 페이지에 연결된 SDS PDF를 함께 다운로드합니다",
    )
    parser.add_argument(
        "--sds-languages",
        nargs="+",
        help="SDS를 다운로드할 언어 코드 목록 (예: ko en). 기본은 페이지에서 제공하는 전체 언어입니다.",
    )
    parser.add_argument(
        "--sds-output-dir",
        default="data/sds",
        help="SDS PDF를 저장할 경로 (저장소 루트 기준)",
    )
    args = parser.parse_args()

    if args.use_existing_session and SESSION_JSON.exists():
        session = json.loads(SESSION_JSON.read_text(encoding="utf-8"))
    else:
        session = refresh_session(args.url)

    cookies = load_cookies(session)
    headers = build_headers()
    requests_session = create_requests_session(headers, cookies)
    html = fetch_html(requests_session, args.url)

    output_path = (REPO_ROOT / args.output).resolve()
    output_path.write_text(html, encoding="utf-8")

    print(f"Saved HTML ({len(html)} bytes) to {output_path}")

    if args.download_sds:
        metadata = parse_sds_metadata(html)
        if not metadata:
            print("SDS 정보를 페이지에서 찾을 수 없습니다.")
            return

        csrf_token = extract_csrf_token(html)
        if not csrf_token:
            print("경고: CSRF 토큰을 찾을 수 없습니다. SDS 다운로드가 실패할 수 있습니다.")

        language_codes = args.sds_languages or [code for code, _ in metadata.languages if code]
        if not language_codes:
            print("SDS 언어 목록이 비어 있어 다운로드를 건너뜁니다.")
            return

        sds_output_dir = (REPO_ROOT / args.sds_output_dir).resolve()
        downloaded = download_sds_documents(
            requests_session,
            args.url,
            metadata,
            language_codes,
            sds_output_dir,
            csrf_token,
        )
        if not downloaded:
            print("SDS 파일을 다운로드하지 못했습니다.")


if __name__ == "__main__":
    main()

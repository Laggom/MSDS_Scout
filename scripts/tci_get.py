#!/usr/bin/env python3
"""TCI 제품 페이지 HTML과 SDS를 Playwright MCP를 통해 수집합니다."""

from __future__ import annotations

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

from sds_common import DownloadRecord, build_summary, normalize_languages, print_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION_JSON = REPO_ROOT / "data" / "tci_session.json"
URL_DEFAULT = "https://www.tcichemicals.com/KR/ko/p/L0483"


def refresh_session(url: str) -> Dict:
    """Playwright MCP로 헤더와 쿠키를 갱신합니다."""
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


def load_cookies(session: Dict) -> Dict[str, str]:
    """Playwright storageState 형식을 requests 쿠키로 변환합니다."""
    return {cookie["name"]: cookie["value"] for cookie in session.get("cookies", {}).get("cookies", [])}


def build_headers() -> Dict[str, str]:
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
            print(f"경고: 페이지에서 제공하지 않는 언어 코드 '{lang}'는 건너뜁니다.")
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
        except requests.RequestException as exc:
            print(f"- SDS 다운로드 실패({lang}): {exc}")
            continue

        if response.status_code != 200:
            print(f"- SDS 다운로드 실패({lang}): HTTP {response.status_code}")
            continue

        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
            response_text = response.headers.get("response-text") or response.text[:200]
            print(f"- SDS 다운로드 실패({lang}): {response_text}")
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
        print(f"- SDS 저장 완료({lang}): {output_path}")

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
        help="TCI 제품 페이지 URL",
    )
    parser.add_argument(
        "--html-output",
        "--output",
        dest="html_output",
        default="tci_product.html",
        help="HTML을 저장할 파일 경로(저장소 기준)",
    )
    parser.add_argument(
        "--use-existing-session",
        action="store_true",
        help="저장된 세션(JSON)을 재사용합니다.",
    )
    parser.add_argument(
        "--download-sds",
        action="store_true",
        help="SDS PDF까지 함께 다운로드합니다.",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        help="SDS 다운로드 언어 코드 목록 (예: ko en). 비우면 페이지에서 제공하는 모든 언어를 사용합니다.",
    )
    parser.add_argument(
        "--output-dir",
        dest="sds_output_dir",
        default="data/sds",
        help="SDS PDF를 저장할 디렉터리",
    )
    args = parser.parse_args()

    product_url = args.product_url

    if args.use_existing_session and SESSION_JSON.exists():
        session_state = json.loads(SESSION_JSON.read_text(encoding="utf-8"))
    else:
        session_state = refresh_session(product_url)

    requests_session = create_requests_session(build_headers(), load_cookies(session_state))
    html = fetch_html(requests_session, product_url)

    html_output_path = (REPO_ROOT / args.html_output).resolve()
    html_output_path.write_text(html, encoding="utf-8")
    print(f"HTML 저장 완료 ({len(html)} bytes): {html_output_path}")

    metadata = parse_sds_metadata(html)
    product_code = metadata.product_code if metadata else urlparse(product_url).path.rstrip("/").split("/")[-1]

    records: List[DownloadRecord] = []
    if args.download_sds:
        if not metadata:
            print("SDS 메타데이터를 페이지에서 찾지 못했습니다.")
        else:
            csrf_token = extract_csrf_token(html)
            if not csrf_token:
                print("경고: CSRF 토큰을 찾지 못했습니다. SDS 다운로드가 실패할 수 있습니다.")

            requested_languages = normalize_languages(args.languages) or [
                code for code, _ in metadata.languages if code
            ]
            if not requested_languages:
                print("다운로드할 언어가 없어 SDS를 건너뜁니다.")
            else:
                sds_output_dir = (REPO_ROOT / args.sds_output_dir).resolve()
                records = download_sds_documents(
                    requests_session,
                    product_url,
                    metadata,
                    requested_languages,
                    sds_output_dir,
                    csrf_token,
                )
                if not records:
                    print("SDS 파일을 다운로드하지 못했습니다.")

    summary = build_summary(
        provider="tci",
        product_identifier=product_code,
        product_url=product_url,
        html_path=html_output_path,
        downloads=records,
        notes={"sessionPath": str(SESSION_JSON)},
    )
    print_summary(summary)


if __name__ == "__main__":
    main()

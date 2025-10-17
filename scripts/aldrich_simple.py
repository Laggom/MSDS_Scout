#!/usr/bin/env python3
"""Simple Sigma-Aldrich SDS downloader without session management."""

import argparse
import re
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]


def download_sds_simple(
    product_url: str,
    languages: list,
    output_dir: Path,
) -> list:
    """Download SDS PDF documents directly."""
    # Extract info from URL
    url_match = re.match(
        r"https://www\.sigmaaldrich\.com/([A-Z]{2})/([a-z]{2})/product/([^/]+)/([^/?]+)",
        product_url
    )
    if not url_match:
        print(f"잘못된 URL 형식: {product_url}")
        print("예: https://www.sigmaaldrich.com/KR/ko/product/sigald/34873")
        return []

    country = url_match.group(1)
    default_lang = url_match.group(2)
    brand = url_match.group(3)
    product_number = url_match.group(4)

    print(f"제품: {product_number}")
    print(f"브랜드: {brand}")
    print(f"국가: {country}")

    # If no languages specified, use default from URL
    if not languages:
        languages = [default_lang]

    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded_files = []

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    })

    for lang in languages:
        lang = lang.strip().lower()
        if not lang:
            continue

        # SDS URL: https://www.sigmaaldrich.com/{COUNTRY}/{LANG}/sds/{BRAND}/{PRODUCT}
        sds_url = f"https://www.sigmaaldrich.com/{country}/{lang}/sds/{brand}/{product_number}"

        print(f"\nSDS 다운로드 시도 ({lang}): {sds_url}")

        try:
            response = session.get(sds_url, timeout=30, allow_redirects=True)

            if response.status_code != 200:
                print(f"  ✗ 실패: HTTP {response.status_code}")
                continue

            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type:
                print(f"  ✗ 실패: PDF가 아님 (Content-Type: {content_type})")
                continue

            filename = f"{product_number}_{country}_{lang.upper()}.pdf"
            output_path = output_dir / filename
            output_path.write_bytes(response.content)

            size_kb = len(response.content) / 1024
            print(f"  ✓ 저장: {output_path} ({size_kb:.1f} KB)")
            downloaded_files.append(output_path)

        except Exception as e:
            print(f"  ✗ 오류: {e}")
            continue

    return downloaded_files


def main():
    parser = argparse.ArgumentParser(
        description="Sigma-Aldrich SDS 다운로더 (간단 버전, 세션 관리 없음)"
    )
    parser.add_argument(
        "url",
        help="제품 페이지 URL (예: https://www.sigmaaldrich.com/KR/ko/product/sigald/34873)"
    )
    parser.add_argument(
        "-l", "--languages",
        nargs="+",
        default=[],
        help="언어 코드 (예: ko en). 지정하지 않으면 URL의 언어 사용"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="data/sds_aldrich",
        help="SDS 저장 디렉토리 (기본: data/sds_aldrich)"
    )

    args = parser.parse_args()

    output_dir = (REPO_ROOT / args.output_dir).resolve()

    downloaded = download_sds_simple(
        args.url,
        args.languages,
        output_dir
    )

    print(f"\n{'='*60}")
    if downloaded:
        print(f"✓ 성공: {len(downloaded)}개의 SDS 파일 다운로드 완료")
        for file in downloaded:
            print(f"  - {file.name}")
    else:
        print("✗ 실패: 다운로드한 파일이 없습니다")


if __name__ == "__main__":
    main()

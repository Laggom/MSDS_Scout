#!/usr/bin/env python3
"""Batch test runner for the Sigma-Aldrich SDS downloader."""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DOWNLOADER = REPO_ROOT / "scripts" / "aldrich_mcp.py"

# (URL, Description)
TEST_PRODUCTS: List[Tuple[str, str]] = [
    ("https://www.sigmaaldrich.com/KR/ko/product/sigald/34873", "Heptane - HPLC grade"),
    ("https://www.sigmaaldrich.com/KR/ko/product/sial/a7409", "Acetic acid"),
    ("https://www.sigmaaldrich.com/KR/ko/product/sigald/270989", "Acetone"),
    ("https://www.sigmaaldrich.com/KR/ko/product/sial/m7149", "Methanol"),
    ("https://www.sigmaaldrich.com/KR/ko/product/sial/e7023", "Ethanol"),
    ("https://www.sigmaaldrich.com/KR/ko/product/sial/t2949", "Toluene"),
    ("https://www.sigmaaldrich.com/KR/ko/product/mm/102429", "Sulfuric acid"),
    ("https://www.sigmaaldrich.com/KR/ko/product/mm/100317", "Hydrochloric acid"),
    ("https://www.sigmaaldrich.com/KR/ko/product/sial/s5761", "Sodium chloride"),
    ("https://www.sigmaaldrich.com/KR/ko/product/sigald/w303518", "Water - HPLC grade"),
]


def run_downloader(url: str, description: str) -> Tuple[bool, str]:
    print("\n" + "=" * 80)
    print(f"Product: {description}")
    print(f"URL: {url}")
    print("-" * 80)

    command = [
        sys.executable,
        str(DOWNLOADER.relative_to(REPO_ROOT)),
        "--product-url",
        url,
        "-l",
        "ko",
        "en",
    ]

    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        print("  Timeout: downloader exceeded 180 seconds.")
        return False, "timeout"

    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print("---- stderr ----")
        print(result.stderr.strip())

    success = result.returncode == 0
    status = "success" if success else "failed"
    return success, status


def main() -> None:
    if not DOWNLOADER.exists():
        print(f"Downloader not found: {DOWNLOADER}")
        sys.exit(1)

    results: List[Tuple[str, str, bool, str]] = []

    for url, description in TEST_PRODUCTS:
        success, status = run_downloader(url, description)
        results.append((url, description, success, status))

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)

    total = len(results)
    successes = sum(1 for _, _, success, _ in results if success)
    failures = total - successes
    success_rate = (successes / total * 100) if total else 0.0

    print(f"Total products: {total}")
    print(f"Successful: {successes}")
    print(f"Failed: {failures}")
    print(f"Success rate: {success_rate:.1f}%")

    print("\nDetails:")
    for index, (url, description, success, status) in enumerate(results, start=1):
        marker = "OK" if success else "XX"
        print(f"{index:2d}. {marker} {description:30s} - {status}")

    if failures:
        failure_reasons = {}
        for _, description, success, status in results:
            if not success:
                failure_reasons[status] = failure_reasons.get(status, 0) + 1

        print("\nFailure reasons:")
        for reason, count in sorted(failure_reasons.items(), key=lambda item: item[1], reverse=True):
            print(f"  {reason}: {count}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Test Sigma-Aldrich SDS downloader with multiple products."""

import sys
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]

# Test with various Sigma-Aldrich products
test_products = [
    # Format: (URL, Description)
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

def test_product(url: str, description: str, lang: str = "ko"):
    """Test SDS download for a single product."""
    print(f"\n{'='*70}")
    print(f"테스트: {description}")
    print(f"URL: {url}")
    print('-'*70)

    try:
        result = subprocess.run(
            ["python3", "scripts/aldrich_simple.py", url, "-l", lang],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout
        print(output)

        # Check if successful
        if "✓ 성공:" in output and result.returncode == 0:
            return True, "성공"
        elif "✗ 실패: HTTP 404" in output:
            return False, "404 - SDS 없음"
        elif "✗ 실패:" in output:
            return False, "다운로드 실패"
        else:
            return False, "알 수 없는 오류"

    except subprocess.TimeoutExpired:
        print("  ✗ 타임아웃")
        return False, "타임아웃"
    except Exception as e:
        print(f"  ✗ 오류: {e}")
        return False, str(e)

def main():
    print("="*70)
    print("Sigma-Aldrich SDS 다운로더 - 여러 제품 테스트")
    print("="*70)
    print(f"총 {len(test_products)}개 제품 테스트")

    results = []

    for url, description in test_products:
        success, message = test_product(url, description)
        results.append({
            "url": url,
            "description": description,
            "success": success,
            "message": message,
        })

    # Summary
    print("\n" + "="*70)
    print("테스트 결과 요약")
    print("="*70)

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0

    print(f"\n총 테스트: {total_count}개")
    print(f"성공: {success_count}개")
    print(f"실패: {total_count - success_count}개")
    print(f"성공률: {success_rate:.1f}%")

    print("\n상세 결과:")
    print("-"*70)
    for i, result in enumerate(results, 1):
        status = "✓" if result["success"] else "✗"
        print(f"{i:2d}. {status} {result['description']:30s} - {result['message']}")

    # Failure analysis
    failures = [r for r in results if not r["success"]]
    if failures:
        print("\n실패 원인 분석:")
        print("-"*70)
        failure_reasons = {}
        for f in failures:
            reason = f["message"]
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True):
            print(f"  {reason}: {count}개")

    print("\n" + "="*70)

if __name__ == "__main__":
    main()

# Thermo Fisher SDS 다운로더 (한국어 안내)

Thermo Fisher Chemicals 제품·카테고리 페이지를 순회하면서 공개 API를 호출해 안전보건자료(SDS) PDF를 내려받는 Python 스크립트입니다. 인증이 필요 없으며, API가 반환하는 뷰어 URL에서 PDF를 직접 저장합니다.

## 준비 사항
- Python 3.11 이상
- `requests` (이미 `requirements.txt`에 포함)

## 스크립트 개요
- 경로: `scripts/thermofisher_sds.py`
- 역할: Thermo Fisher APAC 카테고리/제품 API를 호출해 공개된 child SKU를 수집하고, 원하는 언어의 SDS를 저장합니다.

## 사용법
- 카테고리 전체 다운로드 (예: 최대 100개 제품):
  ```bash
  python scripts/thermofisher_sds.py \
    --category-url https://chemicals.thermofisher.kr/apac/search/category/80013495 \
    --max-products 100 \
    --languages ko en \
    --output-dir data/sds_thermofisher
  ```
- 특정 제품만 다운로드:
  ```bash
  python scripts/thermofisher_sds.py \
    --product-url https://chemicals.thermofisher.kr/apac/product/B21525 \
    --languages ko \
    --output-dir data/sds_thermofisher
  ```
- 검색어(물질명 · CAS)로 최상위 제품을 찾아 다운로드:
  ```bash
  python scripts/thermofisher_sds.py \
    --search-term ethanol \
    --languages ko \
    --output-dir data/sds_thermofisher
  ```

## 주요 옵션
| 옵션 | 설명 | 기본값 |
| --- | --- | --- |
| `--category-url` | 순회할 카테고리 URL | `--product-url`과 둘 중 하나 필수 |
| `--product-url` | 제품 상세 페이지 URL (여러 번 지정 가능) | `--category-url`과 둘 중 하나 필수 |
| `-l`, `--languages` | 원하는 언어 코드 (`ko`, `en` 등). `ko-kr` 형태도 자동 정규화됩니다. | `ko en` |
| `-o`, `--output-dir` | PDF 저장 경로 | `data/sds_thermofisher` |
| `--page-size` | 카테고리 API 페이지 크기 | `30` |
| `--max-products` | 카테고리에서 처리할 최대 제품 수 | 제한 없음 |
| `--search-term` | 검색어(물질명 · CAS)로 최상위 결과 제품을 사용 | 사용 안 함 |

## 출력 예시
```
=== SDS Download Summary ===
{
  "provider": "thermofisher",
  "product": "category",
  "downloads": [
    {
      "path": "C:\\...\\B21525_KO.pdf",
      "languages": ["ko"],
      "sourceUrl": "https://assets.thermofisher.com/directwebviewer/private/results.aspx?page=NewSearch&LANGUAGE=d__KO&SUBFORMAT=d__KOSD&SKU=ALFAAB21525&PLANT=d__ALF",
      "metadata": {
        "rootSku": "B21525"
      }
    }
  ],
  "productUrl": "https://chemicals.thermofisher.kr/apac/search/category/80013495",
  "notes": {
    "mode": "category",
    "categoryId": "80013495",
    "totalProducts": 100,
    "products": ["B21525", "..."]
  }
}
```

## 동작 방식
1. 카테고리 URL 또는 제품 URL을 기반으로 APAC API 호출에 필요한 쿠키를 초기화합니다.
2. `/apac/api/search/category` 또는 `/apac/api/search/catalog/keyword`에서 제품 정보를 수집합니다.
3. `/apac/api/search/catalog/child`로 공개된 child SKU 목록을 가져옵니다.
4. `/apac/api/document/search/sds`를 언어별로 호출해 뷰어 URL을 확보하고 PDF를 다운로드합니다.
5. 파일을 `{rootSku}_{LANG}.pdf` 형식으로 저장하고 요약 정보를 출력합니다.

## 참고
- Thermo Fisher API는 `country=kr`, 난수 `com-tf-dye` 헤더를 요구하며 스크립트가 자동 처리합니다.
- 카테고리 모드는 매우 많은 PDF를 생성할 수 있으므로 `--max-products`로 조절하세요.
- 언어별 PDF가 존재하지 않으면 경고 후 건너뜁니다.

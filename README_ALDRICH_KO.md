# Sigma-Aldrich SDS 다운로더 (한국어 안내)

Sigma-Aldrich 제품 페이지에서 안전보건자료(SDS)를 내려받을 수 있도록 Playwright MCP와 Python 스크립트를 묶어 둔 도구입니다. Playwright MCP 설치가 끝나면 동일한 설정으로 TCI, Thermo Fisher 워크플로와 함께 사용할 수 있습니다.

## 준비 사항
- Python 3.11 이상
- Node.js 18 이상
- Playwright MCP 의존성 (`npm install`)
- Playwright 브라우저 바이너리 (`npm run playwright:install`)

## 스크립트 개요
- 경로: `scripts/aldrich_mcp.py`
- 역할: Node 헬퍼 `scripts/download_sds_with_playwright.js`를 호출해 요청한 언어의 SDS PDF를 Playwright APIRequestContext로 다운로드합니다.

## 사용법
```bash
python scripts/aldrich_mcp.py \
  --product-url https://www.sigmaaldrich.com/KR/ko/product/sigald/34873 \
  --languages ko en \
  --output-dir data/sds_aldrich
```

## 주요 옵션
| 옵션 | 설명 | 기본값 |
| --- | --- | --- |
| `--product-url` | 제품 상세 페이지 URL (예: `https://www.sigmaaldrich.com/KR/ko/product/sigald/34873`) | 필수 |
| `-l`, `--languages` | 다운로드할 언어 코드 (예: `ko en`). 비우면 URL에 포함된 언어를 사용합니다. | URL에 포함된 언어 |
| `-o`, `--output-dir` | PDF 저장 경로 | `data/sds_aldrich` |

## 출력 예시
```
=== SDS Download Summary ===
{
  "provider": "aldrich",
  "product": "34873",
  "downloads": [
    {
      "path": "C:\\...\\34873_KR_EN.pdf",
      "languages": ["en"],
      "sourceUrl": "https://www.sigmaaldrich.com/KR/en/sds/sigald/34873"
    },
    {
      "path": "C:\\...\\34873_KR_KO.pdf",
      "languages": ["ko"],
      "sourceUrl": "https://www.sigmaaldrich.com/KR/ko/sds/sigald/34873"
    }
  ],
  "productUrl": "https://www.sigmaaldrich.com/KR/ko/product/sigald/34873"
}
```

요청한 언어의 SDS가 존재하지 않으면 HTTP 상태 코드와 함께 건너뛰며, 다운로드가 한 건도 없을 경우 종료 코드 1을 반환합니다.

## 동작 방식
1. 제품 URL에서 국가/언어/브랜드/제품번호를 파싱합니다.
2. Playwright MCP(`scripts/fetchHeaders.js`)로 최신 쿠키와 헤더를 준비합니다.
3. 언어별 SDS URL을 구성하고 Node 헬퍼로 PDF를 다운로드합니다.
4. 파일을 `{제품번호}_{국가코드}_{언어}.pdf` 형식으로 저장하고 요약 JSON을 출력합니다.

## 참고
- Playwright MCP가 설치돼 있지 않으면 헬퍼 스크립트 실행에 실패합니다.
- 반복 다운로드가 필요한 경우 `scripts/test_aldrich_multiple.py`로 여러 URL을 일괄 검증할 수 있습니다.

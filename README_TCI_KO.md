# TCI SDS 수집기 (한국어 안내)

TCI Korea 제품 페이지에서 HTML과 SDS PDF를 수집하는 Python 스크립트입니다. Playwright MCP를 통해 세션 정보를 최신화한 뒤 `requests`로 페이지를 요청합니다.

## 준비 사항
- Python 3.11 이상
- Node.js 18 이상
- Playwright MCP 의존성 (`npm install`)
- Playwright 브라우저 바이너리 (`npm run playwright:install`)

## 스크립트 개요
- 경로: `scripts/tci_get.py`
- 역할: Playwright MCP로 쿠키/헤더를 새로고침하고, 제품 페이지 HTML 저장 및 선택 언어의 SDS PDF 다운로드를 수행합니다.

## 사용법
- HTML만 저장:
  ```bash
  python scripts/tci_get.py \
    --product-url https://www.tcichemicals.com/KR/ko/p/L0483 \
    --html-output data/tci_L0483.html
  ```
- SDS까지 다운로드:
  ```bash
  python scripts/tci_get.py \
    --product-url https://www.tcichemicals.com/KR/ko/p/L0483 \
    --download-sds \
    --languages ko en \
    --output-dir data/sds_tci
  ```

## 주요 옵션
| 옵션 | 설명 | 기본값 |
| --- | --- | --- |
| `--product-url`, `--url` | TCI 제품 페이지 URL | `https://www.tcichemicals.com/KR/ko/p/L0483` |
| `--html-output`, `--output` | 저장할 HTML 파일 경로 | `tci_product.html` |
| `--use-existing-session` | 기존 `data/tci_session.json`을 재사용 | 새로 갱신 |
| `--download-sds` | SDS PDF까지 내려받기 | 사용 안 함 |
| `--languages` | 다운로드할 언어 코드 (예: `ko en`). 비우면 페이지에 노출된 모든 언어 사용 | 페이지 노출 언어 |
| `--output-dir` | SDS PDF 저장 폴더 | `data/sds` |

## 출력 예시
```
HTML 저장(123456 bytes): C:\...\tci_product.html
- SDS 다운로드(ko): C:\...\data\sds_tci\L0483_KO.pdf
- SDS 다운로드(en): C:\...\data\sds_tci\L0483_EN.pdf

=== SDS Download Summary ===
{
  "provider": "tci",
  "product": "L0483",
  "downloads": [...],
  "htmlPath": "C:\\...\\tci_product.html",
  "notes": {
    "sessionPath": "C:\\...\\data\\tci_session.json"
  }
}
```

## 동작 방식
1. `scripts/fetchHeaders.js`를 호출해 Playwright MCP가 최신 쿠키와 헤더를 갱신합니다(필요 시 `data/tci_session.json`에 저장).
2. 저장된 헤더·쿠키로 제품 페이지 HTML을 내려받아 지정한 파일에 기록합니다.
3. 페이지의 SDS 메타데이터에서 언어, 제품 코드, 컨텍스트 경로를 추출합니다.
4. `--download-sds`가 지정되면 언어별로 다운로드 URL을 호출하고 `{제품코드}_{LANG}.pdf` 형식으로 저장합니다.
5. 모든 작업 결과를 JSON 요약으로 출력합니다.

## 참고
- Playwright MCP가 설치되어 있지 않으면 세션 갱신 단계에서 실패합니다.
- `--use-existing-session`을 사용하면 이미 저장된 세션을 재활용하므로 빠르게 재다운로드할 수 있습니다.
- CSRF 토큰을 찾지 못하면 일부 SDS 요청이 실패할 수 있으며 스크립트가 경고를 출력합니다.

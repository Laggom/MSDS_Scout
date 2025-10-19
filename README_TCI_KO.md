# TCI SDS 수집기 (한국어 안내)

TCI Korea 제품 페이지에서 HTML과 SDS PDF를 내려받는 Python 스크립트입니다. 이제 Playwright MCP에 의존하지 않고 [`curl-cffi`](https://github.com/yifeikong/curl_cffi)를 사용해 브라우저와 유사한 TLS/HTTP 지문으로 요청을 보냅니다.

## 준비 사항
- Python 3.11 이상
- `requests`
- `curl-cffi`

설치는 다음 명령으로 완료할 수 있습니다.

```bash
python -m pip install -r requirements.txt
```

## 스크립트 개요
- 경로: `scripts/tci_get.py`
- 기능: 제품 페이지 HTML을 저장하고, 필요한 경우 언어별 SDS PDF를 직접 다운로드합니다.

## 사용 방법
- HTML만 저장:
  ```bash
  python scripts/tci_get.py \
    --product-url https://www.tcichemicals.com/KR/ko/p/L0483 \
    --html-output tci_product.html
  ```
- SDS까지 함께 다운로드:
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
| `--download-sds` | SDS PDF까지 다운로드 | 사용 안 함 |
| `--languages` | 다운로드할 언어 코드 (`ko`, `en` 등). 생략 시 페이지에 노출된 언어 전체를 사용 | 페이지 언어 목록 |
| `--output-dir` | SDS PDF 저장 폴더 | `data/sds` |
| `--use-existing-session` | 하위 호환용 플래그. 현재 동작에는 영향 없음 | 사용 안 함 |

## 동작 방식
1. `curl-cffi` 세션(Chrome 120 모방)으로 제품 페이지를 호출해 HTML과 쿠키를 확보합니다.
2. HTML에서 제품 코드, 국가, 언어 목록, CSRF 토큰을 추출합니다.
3. SDS 다운로드가 요청되면 해당 정보를 기반으로 `/documentSearch/productSDSSearchDoc` 엔드포인트에 폼 데이터를 제출합니다.
4. 응답이 PDF인지 확인한 뒤 `{제품코드}_{언어}.pdf`로 저장하고 JSON 요약을 출력합니다.

## 참고 및 문제 해결
- 제품 페이지에 언어 옵션이 없으면 SDS 다운로드가 생략됩니다.
- CSRF 토큰이 누락된 경우 서버에서 거부될 수 있으며, 이때는 재시도하거나 브라우저에서 SDS 가능 여부를 확인하세요.
- 네트워크에서 AWS Akamai 도메인이 차단되어 있으면 `RequestsError` 또는 Timeout이 발생할 수 있습니다.

---
마지막 업데이트: 2025-10-19

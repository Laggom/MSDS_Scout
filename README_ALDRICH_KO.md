# Sigma-Aldrich SDS 다운로드 (한국어 안내)

이 저장소는 Playwright 없이 Sigma-Aldrich 안전보건자료(SDS)를 내려받는 Python 스크립트를 제공합니다. [`curl-cffi`](https://github.com/yifeikong/curl_cffi) 라이브러리를 이용해 최신 Chrome과 유사한 TLS/HTTP 지문으로 요청을 보내기 때문에 웹사이트가 요청을 차단하지 않습니다.

## 준비 사항
- Python 3.11 이상
- `requests`
- `curl-cffi`

필요한 패키지는 다음 명령으로 설치할 수 있습니다.

```bash
python -m pip install -r requirements.txt
```

## 스크립트 개요
- 경로: `scripts/aldrich_mcp.py`
- 용도: 지정한 언어의 SDS PDF를 직접 HTTPS 요청으로 다운로드합니다. (Playwright MCP, Node 헬퍼 사용 안 함)

## 사용 예시
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
| `-l`, `--languages` | 다운로드할 언어 코드 (예: `ko en`). 생략하면 URL에 포함된 언어만 다운로드합니다. | URL 언어 |
| `-o`, `--output-dir` | PDF 저장 디렉터리 | `data/sds_aldrich` |

## 동작 방식
1. 제품 URL에서 국가/언어/브랜드/제품 번호를 파싱합니다.
2. `curl-cffi` 세션(Chrome 120 모방)으로 제품 페이지를 한 번 호출해 Akamai 쿠키를 확보합니다.
3. 같은 세션으로 언어별 SDS PDF를 요청하고 `{제품번호}_{국가코드}_{언어}.pdf` 형식으로 저장합니다.
4. 다운로드 결과를 JSON 요약으로 출력합니다.

## 문제 해결
| 증상 | 원인 | 해결 방법 |
| --- | --- | --- |
| HTTP 404 | 해당 언어의 SDS 미제공 | 브라우저로 확인하거나 다른 언어로 시도 |
| Timeout | 서버 응답 지연 또는 네트워크 차단 | 재시도하거나 네트워크 설정 확인 |
| `RequestsError` | Akamai가 TLS 지문을 거부 | `curl-cffi`를 최신 버전으로 업데이트 후 재시도 |

---
마지막 업데이트: 2025-10-19

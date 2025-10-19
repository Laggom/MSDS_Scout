# 프로젝트 개요

이 저장소는 세 공급사(Sigma-Aldrich, TCI, Thermo Fisher)의 안전보건자료(SDS)를 수집하는 도구 모음입니다. Python 스크립트는 [`curl-cffi`](https://github.com/yifeikong/curl_cffi)를 활용해 브라우저와 유사한 TLS 지문으로 직접 HTTPS 요청을 수행하며, 더 이상 Playwright MCP에 의존하지 않습니다. Playwright MCP 관련 설정은 디버깅용으로만 남겨 두었습니다.

## 빠른 시작

```bash
python -m pip install -r requirements.txt
```

`requests`와 `curl-cffi`만 설치하면 되며, Node.js나 Playwright 설치는 필요하지 않습니다.

## SDS 스크립트

| 스크립트 | 용도 | 비고 |
| --- | --- | --- |
| `scripts/aldrich_mcp.py` | Sigma-Aldrich 제품 SDS PDF를 언어별로 다운로드 | `curl-cffi` Chrome 모방 세션으로 Akamai 쿠키 확보 후 PDF 직접 수집 |
| `scripts/tci_get.py` | TCI 제품 페이지 HTML 저장·SDS 다운로드 | 동일 세션으로 요청, `--search-term`(물질명·CAS) 지원, JSON 요약 출력 |
| `scripts/thermofisher_sds.py` | Thermo Fisher 카테고리/제품 API 크롤링·SDS 다운로드 | 공개 JSON API 활용 (`requests`), `--search-term` 제공 |

모든 스크립트는 실행 결과를 JSON 요약으로 출력하여 다운로드 경로와 메타데이터를 한눈에 확인할 수 있습니다.

## 선택 사항: Playwright MCP 서버

디버깅 용도로 Playwright MCP 서버가 필요하다면 다음 명령으로 준비할 수 있습니다.

```bash
npm install
npm run playwright:install
```

- `npm run mcp` : GUI 모드 브라우저와 함께 MCP 서버 실행
- `npm run mcp:headless` : 헤드리스 모드 실행

MCP 클라이언트 설정 예시는 다음과 같습니다.

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npm",
      "args": ["run", "mcp"]
    }
  }
}
```

`mcp.config.json`은 기존 구성 그대로 유지되어 있어 Playwright 기반 세션이 필요할 때 참고용으로 사용할 수 있습니다.

## 저장소 구성

- `scripts/` : 공급사별 Python 스크립트와 공용 유틸리티
- `data/` : PDF와 세션 데이터를 기본적으로 저장하는 디렉터리
- `README_*` : 공급사별 안내 문서(한국어 버전)
- `.playwright-mcp-output/` : MCP 서버 실행 시 생성되는 로그(버전 관리 제외)

---
마지막 업데이트: 2025-10-19

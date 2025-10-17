# Playwright MCP 환경 설정

이 프로젝트는 Playwright MCP(Model Context Protocol) 서버를 로컬에서 바로 실행할 수 있도록 필요한 의존성과 설정 파일을 포함합니다. `@playwright/mcp` 패키지를 이미 설치했으며, 커스터마이징 가능한 기본 설정(`mcp.config.json`)과 실행 스크립트를 제공합니다.

## 설치 및 준비
- `npm install` – 패키지 의존성을 설치합니다. (이미 설치되어 있다면 생략해도 됩니다.)
- `npm run playwright:install` – 최초 1회 브라우저 바이너리를 다운로드해 두면 실행 속도가 빨라집니다.

## 실행 방법
- `npm run mcp` – 기본 설정으로 Playwright MCP 서버를 실행합니다. 브라우저는 GUI 모드로 열립니다.
- `npm run mcp:headless` – 동일한 설정에서 브라우저를 헤드리스(headless) 모드로 실행합니다.

MCP 클라이언트에서는 다음과 같이 설정하면 됩니다.

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

## 설정 파일 (`mcp.config.json`)
- `browser.browserName`: 기본 브라우저(`chromium`)를 지정합니다.
- `browser.contextOptions.viewport`: 기본 뷰포트 크기를 정의합니다.
- `capabilities`: 활성화할 MCP 기능 모음입니다. 필요에 따라 추가/삭제할 수 있습니다.
- `outputDir`: 세션 로그, 스냅샷 등을 저장할 로컬 디렉터리입니다.
- `imageResponses`: 클라이언트로 이미지 응답을 전달할지 여부를 제어합니다.
- `timeouts`: 액션/네비게이션 타임아웃을 밀리초 단위로 조정합니다.

필요에 따라 [Playwright MCP README](https://github.com/microsoft/playwright-mcp#readme)의 추가 옵션(예: `allowedHosts`, `storageState`, `secrets` 등)을 `mcp.config.json`에 확장할 수 있습니다.

## 출력물 관리
- `.playwright-mcp-output/` 디렉터리에 실행 결과가 저장됩니다. 사용할 MCP 워크플로에 맞게 경로나 저장 정책을 수정하세요.
- `node_modules/` 등 일시적 파일은 `.gitignore`에 포함되어 있어 버전 관리에 영향을 주지 않습니다.

## TCI 제품 페이지 HTML 추출 자동화
- `scripts/tci_get.py` – Playwright MCP를 통해 최신 쿠키/헤더를 확보한 뒤 `requests`로 HTML을 다운로드합니다.
  - 기본 URL은 `https://www.tcichemicals.com/KR/ko/p/L0483`이며 `--url` 인자로 변경할 수 있습니다.
  - 실행 시 `data/tci_session.json`에 최신 세션 정보가 저장되며, `tci_product.html` 파일에 본문이 기록됩니다.
  - 새 세션 갱신이 필요 없으면 `--use-existing-session` 옵션으로 기존 JSON을 재사용할 수 있습니다.
- Python 의존성은 `python3 -m venv .venv` 후 `./.venv/bin/pip install -r requirements.txt`로 설치하세요.

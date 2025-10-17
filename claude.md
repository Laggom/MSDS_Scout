# TCI Chemicals SDS Downloader

TCI Chemicals 웹사이트에서 제품 정보와 SDS(Safety Data Sheet) 문서를 자동으로 다운로드하는 도구입니다.

## 프로젝트 개요

이 프로젝트는 TCI Chemicals (https://www.tcichemicals.com) 웹사이트에서 화학 제품의 SDS 문서를 자동으로 다운로드할 수 있도록 개발되었습니다. Playwright를 사용하여 브라우저 세션을 관리하고, Python requests로 실제 다운로드를 수행합니다.

## 주요 기능

- ✅ TCI Chemicals 제품 페이지 HTML 다운로드
- ✅ SDS PDF 문서 자동 다운로드
- ✅ 여러 언어(한국어, 영어 등) 지원
- ✅ CSRF 토큰 자동 추출 및 적용
- ✅ Playwright를 통한 쿠키/세션 자동 관리
- ✅ 세션 재사용 기능 (선택적)

## 설치

### 1. Python 의존성 설치

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Node.js 의존성 설치

```bash
npm install
```

## 사용법

### 기본 사용 (HTML만 다운로드)

```bash
python3 scripts/tci_get.py --url https://www.tcichemicals.com/KR/ko/p/L0483
```

### SDS 다운로드 (한국어)

```bash
python3 scripts/tci_get.py \
  --url https://www.tcichemicals.com/KR/ko/p/L0483 \
  --download-sds \
  --sds-languages ko
```

### 여러 언어 SDS 다운로드

```bash
python3 scripts/tci_get.py \
  --url https://www.tcichemicals.com/KR/ko/p/L0483 \
  --download-sds \
  --sds-languages ko en
```

### 기존 세션 재사용

```bash
python3 scripts/tci_get.py \
  --url https://www.tcichemicals.com/KR/ko/p/L0483 \
  --download-sds \
  --sds-languages ko \
  --use-existing-session
```

### 커스텀 출력 경로

```bash
python3 scripts/tci_get.py \
  --url https://www.tcichemicals.com/KR/ko/p/L0483 \
  --output my_product.html \
  --download-sds \
  --sds-output-dir my_sds_folder
```

## 명령줄 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--url` | 다운로드할 제품 페이지 URL | `https://www.tcichemicals.com/KR/ko/p/L0483` |
| `--output` | HTML 저장 경로 (저장소 루트 기준) | `tci_product.html` |
| `--use-existing-session` | 저장된 세션 재사용 (새로 가져오지 않음) | False |
| `--download-sds` | SDS PDF 다운로드 활성화 | False |
| `--sds-languages` | SDS 언어 목록 (공백으로 구분) | 페이지의 모든 언어 |
| `--sds-output-dir` | SDS 저장 경로 (저장소 루트 기준) | `data/sds` |

## 파일 구조

```
Connect/
├── scripts/
│   ├── fetchHeaders.js      # Playwright로 쿠키/헤더 수집
│   └── tci_get.py           # 메인 스크립트 (SDS 다운로드)
├── data/
│   ├── tci_session.json     # 세션 정보 (자동 생성/갱신)
│   └── sds/                 # SDS PDF 저장 디렉토리
├── package.json             # Node.js 의존성
├── requirements.txt         # Python 의존성
├── mcp.config.json          # MCP 설정
└── README.md                # 프로젝트 문서

```

## 기술적 세부사항

### 작동 원리

1. **세션 획득** (fetchHeaders.js)
   - Playwright를 사용하여 실제 브라우저로 TCI 웹사이트 방문
   - 필요한 쿠키와 헤더 정보 수집
   - `data/tci_session.json`에 저장

2. **HTML 다운로드** (tci_get.py)
   - 저장된 세션 정보로 requests 세션 생성
   - 제품 페이지 HTML 다운로드
   - CSRF 토큰 추출

3. **SDS 다운로드** (tci_get.py)
   - HTML에서 SDS 메타데이터 파싱
     - 제품 코드 (sdsProductCode)
     - 국가 코드 (selectedCountry)
     - 사용 가능한 언어 목록 (langSelector)
     - 컨텍스트 경로 (encodedContextPath)
     - CSRF 토큰 (CSRFToken)
   - 각 언어별로 AJAX POST 요청 전송
     - URL: `/KR/ko/documentSearch/productSDSSearchDoc`
     - Content-Type: `application/x-www-form-urlencoded`
     - X-Requested-With: `XMLHttpRequest`
   - PDF 파일 저장

### 핵심 구현 사항

#### CSRF 토큰 처리

TCI Chemicals 웹사이트는 CSRF 보호를 사용합니다. 각 SDS 다운로드 요청에는 페이지에서 추출한 CSRF 토큰이 필요합니다.

```python
# HTML에서 CSRF 토큰 추출
def extract_csrf_token(html: str) -> Optional[str]:
    match = re.search(r"ACC\.config\.CSRFToken\s*=\s*'([^']+)'", html)
    return match.group(1) if match else None

# POST 요청에 CSRF 토큰 포함
data = {
    "productCode": product_code.upper(),
    "langSelector": lang,
    "selectedCountry": country,
    "CSRFToken": csrf_token,  # 필수!
}
```

#### AJAX 요청 헤더

SDS 다운로드는 AJAX 요청으로 이루어지므로 적절한 헤더가 필요합니다.

```python
headers = {
    "Referer": product_url,
    "Origin": base_url,
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",  # AJAX 식별
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}
```

#### 세션 관리

세션은 자동으로 관리되며, 필요시 재생성됩니다:

```bash
# 첫 실행: 새 세션 생성
python3 scripts/tci_get.py --url <URL> --download-sds

# 재실행: 기존 세션 재사용
python3 scripts/tci_get.py --url <URL> --download-sds --use-existing-session
```

### 메타데이터 파싱

HTML에서 추출되는 주요 정보:

```html
<!-- 제품 코드 -->
<input name="sdsProductCode" id="sdsProductCode" type="hidden" value="L0483">

<!-- 국가 코드 -->
<input name="selectedCountry" id="selectedCountry" type="hidden" value="KR">

<!-- 언어 선택 -->
<select id="langSelector" name="langSelector">
    <option value="ko">한국어</option>
    <option value="en">영어</option>
</select>

<!-- JavaScript 설정 -->
<script>
ACC.config.encodedContextPath = '/KR/ko';
ACC.config.CSRFToken = 'aOZY23V5Cpx3T2MD0jdxGd8...';
</script>
```

## 개발 과정 및 문제 해결

### 1단계: 초기 구현 (실패)

처음에는 CSRF 토큰 없이 구현했으나 HTTP 404 에러 발생:

```python
# ❌ 작동하지 않음
data = {
    "productCode": product_code,
    "langSelector": lang,
    "selectedCountry": country,
}
# 결과: HTTP 404 Not Found
```

### 2단계: 디버깅

여러 방법으로 문제 원인 파악:

1. **JavaScript 파일 분석**
   ```bash
   curl https://www.tcichemicals.com/_ui/responsive/common/js/documentSearch.js
   ```
   - jQuery AJAX POST 요청 발견
   - `xhrFields: {responseType: 'blob'}` 확인

2. **Playwright로 실제 요청 캡처**
   ```javascript
   page.on('request', request => {
       console.log(request.postData());  // CSRF 토큰 발견!
   });
   ```

3. **네트워크 요청 비교**
   - 브라우저 요청: 성공 (CSRF 토큰 포함)
   - Python 요청: 실패 (CSRF 토큰 없음)

### 3단계: CSRF 토큰 추가 (성공)

HTML에서 CSRF 토큰을 추출하고 POST 데이터에 포함:

```python
# ✅ 작동함
csrf_token = extract_csrf_token(html)
data = {
    "productCode": product_code,
    "langSelector": lang,
    "selectedCountry": country,
    "CSRFToken": csrf_token,  # 핵심!
}
# 결과: HTTP 200 OK, PDF 다운로드 성공
```

### 4단계: 테스트 및 검증

여러 제품으로 테스트하여 안정성 확인:

```bash
# 5개 제품 테스트
L0483 ✓ (323.7 KB)
A0001 ✓ (363.6 KB)
M0001 ✓ (346.1 KB)
T0001 ✓ (333.7 KB)
B0001 ✗ (제품 미존재)

# 세션 재생성 테스트
rm data/tci_session.json
python3 scripts/tci_get.py --url ... --download-sds
# ✓ 자동으로 새 세션 생성 및 다운로드 성공
```

## 주의사항

1. **세션 유효성**: 세션은 일정 시간이 지나면 만료될 수 있습니다. 오류 발생 시 세션 파일을 삭제하고 재시도하세요.

2. **Rate Limiting**: 너무 많은 요청을 짧은 시간에 보내지 마세요. 서버에 부담을 줄 수 있습니다.

3. **제품 존재 여부**: 존재하지 않는 제품 코드는 HTTP 404 에러를 반환합니다.

4. **언어 가용성**: 모든 제품이 모든 언어로 SDS를 제공하지는 않습니다. 요청한 언어가 없으면 건너뜁니다.

## 트러블슈팅

### HTTP 404 에러

```bash
# 해결 방법 1: 세션 재생성
rm data/tci_session.json
python3 scripts/tci_get.py --url <URL> --download-sds

# 해결 방법 2: URL 확인
# 올바른 URL 형식: https://www.tcichemicals.com/KR/ko/p/[제품코드]
```

### CSRF 토큰 없음 경고

```
경고: CSRF 토큰을 찾을 수 없습니다. SDS 다운로드가 실패할 수 있습니다.
```

이는 HTML 페이지 구조가 변경되었거나 JavaScript가 비활성화되었을 때 발생합니다. 페이지 HTML을 확인하세요.

### Playwright 에러

```bash
# Playwright 브라우저 재설치
npx playwright install chromium
```

## 향후 개발 계획

- [ ] 여러 제품 일괄 다운로드 기능
- [ ] CLI 진행률 표시
- [ ] 다운로드 이력 관리
- [ ] 자동 재시도 로직
- [ ] 병렬 다운로드 지원

## 라이선스

이 프로젝트는 교육 및 연구 목적으로만 사용되어야 합니다. TCI Chemicals의 이용 약관을 준수하세요.

## 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.

---

**마지막 업데이트**: 2025-10-16
**테스트 환경**: macOS, Python 3.13, Node.js 18+

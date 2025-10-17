# Sigma-Aldrich SDS Downloader

Sigma-Aldrich 웹사이트에서 SDS(Safety Data Sheet) 문서를 자동으로 다운로드하는 간단한 도구입니다.

## 특징

- ✅ **세션 관리 불필요**: 복잡한 인증 없이 직접 SDS 다운로드
- ✅ **여러 언어 지원**: 한국어, 영어 등 다양한 언어의 SDS 다운로드
- ✅ **간단한 사용법**: URL만 입력하면 자동 다운로드
- ✅ **여러 번 재접속 가능**: 안정적인 다운로드 지원

## 설치

```bash
# Python 의존성만 필요
pip install requests
```

## 사용법

### 기본 사용 (URL의 언어로 다운로드)

```bash
python3 scripts/aldrich_simple.py https://www.sigmaaldrich.com/KR/ko/product/sigald/34873
```

### 특정 언어로 다운로드

```bash
python3 scripts/aldrich_simple.py https://www.sigmaaldrich.com/KR/ko/product/sigald/34873 -l ko en
```

### 커스텀 출력 디렉토리

```bash
python3 scripts/aldrich_simple.py https://www.sigmaaldrich.com/KR/ko/product/sigald/34873 -l ko -o my_sds_folder
```

## 사용 예시

```bash
# 한국어 SDS만 다운로드
$ python3 scripts/aldrich_simple.py https://www.sigmaaldrich.com/KR/ko/product/sigald/34873 -l ko

제품: 34873
브랜드: sigald
국가: KR

SDS 다운로드 시도 (ko): https://www.sigmaaldrich.com/KR/ko/sds/sigald/34873
  ✓ 저장: /Users/lag/coding/Connect/data/sds_aldrich/34873_KR_KO.pdf (520.5 KB)

============================================================
✓ 성공: 1개의 SDS 파일 다운로드 완료
  - 34873_KR_KO.pdf


# 한국어와 영어 SDS 동시 다운로드
$ python3 scripts/aldrich_simple.py https://www.sigmaaldrich.com/KR/ko/product/sigald/34873 -l ko en

제품: 34873
브랜드: sigald
국가: KR

SDS 다운로드 시도 (ko): https://www.sigmaaldrich.com/KR/ko/sds/sigald/34873
  ✓ 저장: /Users/lag/coding/Connect/data/sds_aldrich/34873_KR_KO.pdf (520.5 KB)

SDS 다운로드 시도 (en): https://www.sigmaaldrich.com/KR/en/sds/sigald/34873
  ✓ 저장: /Users/lag/coding/Connect/data/sds_aldrich/34873_KR_EN.pdf (338.7 KB)

============================================================
✓ 성공: 2개의 SDS 파일 다운로드 완료
  - 34873_KR_KO.pdf
  - 34873_KR_EN.pdf
```

## 명령줄 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `url` (필수) | Sigma-Aldrich 제품 페이지 URL | - |
| `-l, --languages` | 다운로드할 언어 코드 목록 | URL의 언어 |
| `-o, --output-dir` | SDS 저장 디렉토리 | `data/sds_aldrich` |

## URL 형식

Sigma-Aldrich 제품 페이지 URL은 다음 형식이어야 합니다:

```
https://www.sigmaaldrich.com/{COUNTRY}/{LANGUAGE}/product/{BRAND}/{PRODUCT_NUMBER}
```

예시:
- `https://www.sigmaaldrich.com/KR/ko/product/sigald/34873`
- `https://www.sigmaaldrich.com/KR/ko/product/sial/a7409`
- `https://www.sigmaaldrich.com/US/en/product/mm/106404`

## 작동 원리

1. **URL 파싱**: 제품 URL에서 국가, 언어, 브랜드, 제품 번호 추출
2. **SDS 다운로드**: Sigma-Aldrich의 공개 SDS API 사용
   - API 패턴: `https://www.sigmaaldrich.com/{COUNTRY}/{LANG}/sds/{BRAND}/{PRODUCT_NUMBER}`
3. **파일 저장**: `{PRODUCT_NUMBER}_{COUNTRY}_{LANG}.pdf` 형식으로 저장

## TCI Chemicals와의 차이점

| 특징 | Sigma-Aldrich | TCI Chemicals |
|------|---------------|---------------|
| 세션 관리 | 불필요 | 필요 (Playwright) |
| CSRF 토큰 | 불필요 | 필수 |
| 복잡도 | 간단 | 복잡 |
| 다운로드 방식 | 직접 URL | AJAX POST |
| 재사용성 | 매우 높음 | 세션 만료 가능 |

Sigma-Aldrich는 SDS를 공개 API로 제공하기 때문에 별도의 인증이나 세션 관리 없이 간단하게 다운로드할 수 있습니다.

## 테스트 결과

```bash
# 여러 제품 테스트
제품 34873 (sigald): ✓ 성공
제품 a7409 (sial): ✓ 성공
제품 106404 (mm): ✗ 실패 (SDS 없음)
```

성공률: 2/3 (67%)
- 실패한 제품은 SDS가 제공되지 않는 제품

## 주의사항

1. **제품에 따라 SDS가 없을 수 있음**: 모든 제품이 SDS를 제공하지는 않습니다.
2. **언어 가용성**: 요청한 언어의 SDS가 없으면 404 에러가 발생합니다.
3. **네트워크 타임아웃**: 느린 네트워크 환경에서는 타임아웃이 발생할 수 있습니다.

## 트러블슈팅

### HTTP 404 에러

```
✗ 실패: HTTP 404
```

**가능한 원인:**
1. 해당 제품에 SDS가 제공되지 않음
2. 요청한 언어의 SDS가 없음
3. 제품 번호 또는 브랜드 코드가 잘못됨

**해결 방법:**
- 웹 브라우저에서 해당 제품 페이지를 방문하여 SDS가 있는지 확인
- 다른 언어 코드로 시도

### URL 형식 오류

```
잘못된 URL 형식: ...
```

**해결 방법:**
- URL이 `https://www.sigmaaldrich.com/{COUNTRY}/{LANG}/product/{BRAND}/{PRODUCT}` 형식인지 확인
- 제품 페이지 URL을 복사하여 사용

## 향후 개발

- [ ] 일괄 다운로드 기능
- [ ] 재시도 로직
- [ ] 진행률 표시

---

**마지막 업데이트**: 2025-10-16
**테스트 환경**: macOS, Python 3.13

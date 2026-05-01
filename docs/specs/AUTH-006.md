# AUTH-006: Chrome 브라우저 익스텐션 Google OAuth 인증

**상태**: 구현 완료 | **작성일**: 2026-05-01 | **작성자**: yoonsoo
**F-xxx 매핑**: F-AUTH-006 | **단계**: Phase 1 - MVP | **우선순위**: High

---

## 1. 개요

**문제**: Chrome 브라우저 익스텐션에 인증 흐름이 없어, 사용자가 익스텐션에서 로그인할 수 없었음. 저장 및 동기화 기능을 사용하려면 웹 대시보드를 별도로 열어야 했음.

**해결**: `chrome.identity.launchWebAuthFlow`와 `chromiumapp.org` 리다이렉트 URI를 사용해 익스텐션 팝업에서 Google OAuth를 구현하고, 기존 백엔드 `/api/v1/auth/google/code` 엔드포인트로 인증 코드를 교환.

**목표**: 사용자가 익스텐션 팝업에서 Google 계정으로 로그인 가능; 웹 대시보드와 동일한 백엔드 토큰 인프라 공유.

**비목표**: 익스텐션 내 네이버/카카오 로그인, 기기 간 세션 동기화, 익스텐션 전용 토큰 저장소.

---

## 2. 요구사항

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| FR-1 | 익스텐션 팝업의 "Continue with Google" 버튼으로 OAuth 시작 | P0 |
| FR-2 | OAuth 흐름이 Chrome 내장 인증 창에서 실행됨 | P0 |
| FR-3 | 인증 코드는 백엔드를 통해 교환 (클라이언트 시크릿이 익스텐션에 노출되지 않음) | P0 |
| FR-4 | 로그인 성공 시 사용자 이메일과 함께 인증된 팝업 상태 표시 | P0 |
| FR-5 | Google 창을 닫는 경우 에러 없이 자동 취소 처리 | P1 |
| NFR-1 | 리다이렉트 URI는 `https://<익스텐션ID>.chromiumapp.org/` 패턴 사용 | P0 |
| NFR-2 | 백엔드와 동일한 Web OAuth 클라이언트 ID 사용 (코드 교환 시 자격증명 일치) | P0 |

---

## 3. 사용자 스토리 / 동작

사용자로서, 익스텐션에서 Google 계정으로 로그인하여 저장한 페이지가 Briefly 라이브러리에 동기화되기를 원한다.

### 주요 동작

- "Continue with Google" 클릭 시 Chrome 관리 OAuth 팝업 창 열림
- Google 계정 선택 및 권한 동의가 팝업 창에서 이루어짐
- 동의 후 Chrome이 `chromiumapp.org` 리다이렉트를 가로채어 익스텐션에 코드 반환
- 익스텐션이 코드와 리다이렉트 URI를 백엔드로 전송하여 토큰 교환
- 성공 시 팝업이 인증된 "READY TO CAPTURE" 화면으로 전환

---

## 4. 데이터 모델

### 신규 테이블

없음.

### 기존 사용

- `user_profiles` (첫 로그인 시 사용자 조회/생성)
- `user_auth_methods` (기존 `/auth/google/code` 흐름을 통한 Google 인증 레코드)

---

## 5. API 설계

기존 엔드포인트 사용:

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/v1/auth/google/code` | POST | Google 인증 코드를 Briefly 액세스 + 리프레시 토큰으로 교환 |

### 요청

```json
{
  "code": "<google_auth_code>",
  "redirect_uri": "https://<익스텐션ID>.chromiumapp.org/"
}
```

### 응답 (200 OK)

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_at": "...",
  "user": { "id": 1, "email": "user@gmail.com" }
}
```

---

## 6. 구현

### 파일

- `browser-extension/src/popup/popup.ts` — `chrome.identity.launchWebAuthFlow`를 사용한 `loginBtn` 클릭 핸들러
- `browser-extension/src/shared/auth.ts` — `loginWithGoogleCode(code, redirectUri)` 백엔드 전송
- `browser-extension/.env` — `VITE_GOOGLE_CLIENT_ID`를 Web OAuth 클라이언트 ID로 설정

### 핵심 로직

1. `client_id`, `redirect_uri=https://<chrome.runtime.id>.chromiumapp.org/`, `response_type=code`, 오프라인 스코프로 인증 URL 구성
2. `chrome.identity.launchWebAuthFlow({ url: authUrl, interactive: true })` 호출
3. Chrome이 `*.chromiumapp.org` 리다이렉트를 가로채고 전체 리다이렉트 URL 반환
4. 반환된 URL의 쿼리 파라미터에서 `code` 추출
5. `authManager.loginWithGoogleCode(code, redirectUri)` 호출 → 백엔드가 코드를 토큰으로 교환
6. 성공 시 인증된 팝업 화면 표시

### Google Cloud Console 설정

- **OAuth 클라이언트 타입**: Web application (백엔드 코드 교환에 사용하는 클라이언트와 동일)
- **승인된 리다이렉트 URI 추가**: `https://<익스텐션ID>.chromiumapp.org/`
- **참고**: 익스텐션을 unpacked로 로드하는 개발자마다 다른 익스텐션 ID가 생성되므로, 각자 자신의 `chromiumapp.org` URI를 콘솔에 추가해야 함. Chrome 웹 스토어에 배포하면 ID가 고정됨.

### 버그 수정: OAuth 콜백 이중 실행

`web-dashboard/src/pages/OAuthCallback.tsx`에서 React StrictMode의 이중 호출로 인해 토큰 교환이 두 번 발생하는 문제 수정. `useEffect` 의존성 배열을 `[location, navigate, authStore]`에서 `[]`로 변경하고, 모든 `navigate()` 호출에 `{ replace: true }` 추가.

### 의존성

**필요 (충족됨)**:
- AUTH-002 — 기존 `/auth/google/code` 백엔드 엔드포인트
- AUTH-005 — 사용자 생성을 위한 `user_auth_methods` 인증 테이블

**제공 (향후)**:
- 익스텐션 팝업에 네이버/카카오 로그인 버튼 추가 기반

---

## 7. 엣지 케이스

| 시나리오 | 처리 방식 |
|----------|-----------|
| 사용자가 Google 인증 창 닫기 | `launchWebAuthFlow`가 'cancelled'/'closed' 메시지로 throw → 에러 없이 자동 취소 처리 |
| `chrome.runtime.id` 사용 불가 | 인증 URL 구성 실패; `if (!clientId)` 검사로 가드 |
| 백엔드 교환 실패 (잘못된 자격증명) | 익스텐션 팝업에 `showError()`로 에러 표시 |
| 익스텐션 저장소의 만료된 리프레시 토큰 | chrome://extensions/ 오류 패널에 일시적 리프레시 에러 표시; 새 로그인 차단하지 않음 |
| 개발자마다 다른 익스텐션 ID | 개발 중 각 개발자가 본인의 `chromiumapp.org` URI를 Google Cloud Console에 직접 등록 필요 |

---

## 8. 테스트

- **단위**: 코드 URL을 반환하는 `chrome.identity.launchWebAuthFlow` mock; 취소 흐름이 에러 없이 반환
- **통합**: 버튼 클릭 → Google 팝업 → 코드 → 백엔드 교환 → 인증 상태까지 전체 흐름
- **인수**: 로그인 후 팝업에 사용자 이메일 표시; "Save current page" 기능 활성화

---

## 9. 감각 검증

- **시각**: 로그인 후 팝업 상단에 "READY TO CAPTURE" 표시, 우측 상단에 사용자 이메일 표시; 로그인 화면이 저장 컨트롤로 교체됨
- **청각**: 백엔드 로그에 `/auth/google/code` 성공 호출 기록; 익스텐션 팝업 DevTools 콘솔에 오류 없음
- **촉각**: 버튼 클릭 후 ~1초 내 Google 팝업 열림; 권한 동의 후 ~2초 내 인증 상태 전환

---

## 10. 향후 개선사항

1. `manifest.json`에 `oauth2` 키 추가로 `chrome.identity.getAuthToken` 흐름 지원 (개발자별 리다이렉트 URI 등록 불필요)
2. 익스텐션 팝업에 네이버/카카오 로그인 버튼 추가
3. 토큰 만료 시 자동 재인증 (`chrome.identity`를 통한 무음 토큰 갱신)

---

## 11. 참고

- [AUTH-002.md](AUTH-002.md) — Google OAuth 백엔드 구현
- [AUTH-005.md](AUTH-005.md) — 멀티 프로바이더 인증 레이어
- [EXT-001.md](EXT-001.md) — 브라우저 익스텐션 아키텍처
- [Chrome Identity API 문서](https://developer.chrome.com/docs/extensions/reference/identity/)

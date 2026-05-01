# TODOS — Briefly

/autoplan에서 자동으로 생성됨. 2026-04-10.

---

## 🔑 Google OAuth 공통 설정 (팀 공유 작업 — 담당자 미지정)

> **현황**: 백엔드, 웹, iOS 모두 Google 로그인 코드는 준비됨.
> Google Cloud Console에서 클라이언트 ID를 발급하지 않아 실제 동작 불가.
> **한 명이 아래를 완료하면 전 플랫폼이 Google 로그인 가능.**

### 1. Google Cloud Console 설정

- [ ] [console.cloud.google.com](https://console.cloud.google.com) 에서 팀 공용 프로젝트 생성 (또는 기존 프로젝트 사용)
- [ ] APIs & Services → OAuth 동의 화면 구성
- [ ] 아래 클라이언트 ID 3종 발급:

| 타입 | 용도 | 필요 정보 |
|------|------|-----------|
| **Web application** | 백엔드 서버 + 웹 대시보드 + 브라우저 익스텐션 | Redirect URI 등록 |
| **iOS** | iOS 앱 | Bundle ID: `com.briefly.app` |

### 2. 발급 후 각 플랫폼에 적용

- [ ] **백엔드** (`.env`):
  ```
  GOOGLE_CLIENT_ID=발급받은-web-client-id.apps.googleusercontent.com
  GOOGLE_CLIENT_SECRET=발급받은-client-secret
  ```

- [ ] **브라우저 익스텐션** (`browser-extension/.env`):
  ```
  VITE_GOOGLE_CLIENT_ID=발급받은-web-client-id.apps.googleusercontent.com
  ```

- [ ] **웹 대시보드** (`web-dashboard/.env`):
  ```
  VITE_GOOGLE_CLIENT_ID=발급받은-web-client-id.apps.googleusercontent.com
  ```

- [ ] **iOS** — Google Cloud Console에서 iOS 클라이언트 ID 생성 후:
  - `GoogleService-Info.plist` 다운로드
  - Xcode 프로젝트의 `Briefly` 타겟에 추가 (Target Membership: Briefly만)
  - Xcode → Briefly 타겟 → Info → URL Types에 `REVERSED_CLIENT_ID` 값 추가

> 참고 스펙: `docs/specs/IOS-002.md` (iOS 상세 설명)

---

## Phase 2 (AI 요약) — prototype-1 이후

- [ ] Claude API (claude-haiku-4-5) 연동
- [ ] URLSession + SwiftSoup HTML 파싱
- [ ] async/await 비동기 처리
- [ ] API 키 관리 (Keychain 사용, 하드코딩 금지)
- [ ] 요약 결과 SavedItem에 저장

## Phase 3 (Swipe UX) — Phase 2 이후

- [ ] DragGesture 카드 스택 구현
- [ ] CardStackView.swift
- [ ] SummaryCardView.swift
- [ ] Right Swipe → Keep (태그 저장)
- [ ] Left Swipe → Discard (아카이브)
- [ ] 게이미피케이션: 하루 소화 카드 수 표시

## 배포 인프라 — 필요시

- [ ] Apple Developer 계정 설정 확인 (팀 내 보유자)
- [ ] TestFlight Ad-hoc 배포 설정
- [ ] GitHub Actions CI (빌드 확인)

## 전략 (CEO 리뷰에서 도출)

- [ ] Readwise Reader 대비 Briefly 차별점 1줄 정의
- [ ] 5명 유저 인터뷰 (3줄 요약 포맷 검증)
- [ ] 성공 지표 정의: "5명이 1주일 안에 각 3개 이상 링크 저장"

## 코드 품질

- [ ] BrieflyTests/ 유닛 테스트 작성 (test plan: ~/.gstack/projects/...)
- [ ] DESIGN.md 작성 (Phase 2 전에 /design-consultation 실행)

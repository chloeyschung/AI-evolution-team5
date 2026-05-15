# ARCH-017: iOS 인증 방식 — Apple Sign-In 제외, Google + Email/Password만 지원

**Date:** 2026-04-30
**Status:** accepted
**ADR Version:** 1.0.0
**Last Updated:** 2026-04-30
**Owners:** Briefly PM (suyoung)

---

## Context

Briefly iOS 앱에 백엔드 인증을 연동하면서 어떤 로그인 방식을 지원할지 결정이 필요했다.

초기 구현 시 Apple Sign-In이 포함됐으나, 제품 방향 검토 결과 아래 이유로 제외 결정.

## Decision

iOS 앱에서 지원하는 인증 방식:
- **Email/Password** (이메일 + 비밀번호)
- **Google OAuth** (향후 추가 예정)

**Apple Sign-In은 지원하지 않는다.**

## Rationale

- **UX 일관성:** 웹 대시보드가 이미 Google + Email 기반으로 설계되어 있음. 모든 플랫폼에서 동일한 인증 경험 제공.
- **유지보수:** Apple Sign-In은 Apple Developer 계정 설정, Capability 등록, 서버 사이드 토큰 검증이 추가로 필요해 관리 부담이 큼.
- **사용자층:** 목표 사용자는 이미 Google 계정을 가진 웹/모바일 사용자. Apple 전용 계정 의존도가 낮음.
- **백엔드 준비 상태:** `POST /api/v1/auth/login` (이메일), `POST /api/v1/auth/google` 이미 구현 완료.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Apple Sign-In 지원 | Xcode Capability, 서버 사이드 토큰 검증 등 설정 복잡도 높음. 제품 방향과 맞지 않음. |
| Kakao / Naver 추가 | 한국 사용자 타깃이지만 현 단계에서는 우선순위 낮음. ARCH-014 provider enum에 이미 예약되어 있음. |

## Consequences

**Positive:**
- Xcode에서 "Sign in with Apple" Capability 추가 불필요 → 빌드 설정 단순화
- 인증 코드베이스가 한 경로(Email + Google)로 집중

**Negative / trade-offs:**
- Apple App Store 정책: 앱이 소셜 로그인(Google 등)을 제공하는 경우 Apple Sign-In도 제공해야 함. Google OAuth 추가 시 Apple Sign-In을 동시에 추가해야 할 수 있음.
- 현재 이메일 가입 흐름에 이메일 인증(verify-email) 단계가 있어 UX가 소셜 로그인 대비 복잡함.

## Related git history

- 2026-04-30: iOS API 연동 초기 구현 (`AuthTokenStore`, `BrieflyAPI`, `AccountView`)

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-30 | 최초 결정 | — |

## Related

- Specs affected: `docs/specs/IOS-001.md`
- Other ADRs: `ARCH-014` (multi-provider identity)

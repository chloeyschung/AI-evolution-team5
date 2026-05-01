# ARCH-018: iOS 네트워킹 — URLSession 직접 사용, actor 기반 API 클라이언트, DEBUG/RELEASE URL 분리

**Date:** 2026-04-30
**Status:** accepted
**ADR Version:** 1.0.0
**Last Updated:** 2026-04-30
**Owners:** Briefly iOS (suyoung)

---

## Context

IOS-001(iOS ↔ 백엔드 API 연동)을 구현하면서 iOS에서 백엔드를 호출할 네트워킹 레이어를 결정해야 했다.

고려 대상:
- 서드파티 라이브러리 도입 여부 (Alamofire, Moya 등)
- Swift Concurrency(async/await)와의 통합 방식
- Share Extension에서도 동일 클라이언트를 사용할 수 있는지 여부
- 로컬 개발(localhost)과 프로덕션 서버 URL 분리 방법

## Decision

`BrieflyAPI`를 Swift 표준 `URLSession`만 사용하는 `actor`로 구현한다.

주요 결정 사항:

1. **서드파티 네트워킹 라이브러리 미사용** — `URLSession` + `async/await` 직접 사용
2. **`actor BrieflyAPI`** — Swift Concurrency의 actor isolation으로 스레드 안전성 보장
3. **`#if DEBUG / #else` URL 분리** — 빌드 구성으로 URL을 결정, 환경 파일 불필요
4. **ATS `NSExceptionDomains`** — `localhost`만 HTTP 허용, `NSAllowsArbitraryLoads = false` 유지
5. **단일 제네릭 `post<B, R>()` 헬퍼** — 모든 엔드포인트가 동일한 JSON 직렬화 경로 사용
6. **두 타겟 공유** — `AuthTokenStore`·`BrieflyAPI` 모두 Briefly 메인 앱과 BrieflyShareExtension 양쪽 Target Membership에 포함

## Rationale

### URLSession 직접 사용

| 기준 | URLSession | Alamofire/Moya |
|------|-----------|----------------|
| 의존성 | 없음 (iOS SDK 표준) | SPM/CocoaPods 추가 |
| async/await 지원 | iOS 15+ 네이티브 | 별도 wrapper 필요 |
| 빌드 복잡도 | 없음 | Package.swift 항목 추가 |
| Share Extension 호환 | 완전 호환 | Extension 크기 제한(50MB) 주의 |
| 현재 API 수 | 4개 (login, share, refresh, deviceToken) | 과잉 추상화 |

현재 호출 엔드포인트가 4개이며 모두 단순 POST JSON 패턴 — Alamofire의 Router/Moya의 TargetType 추상화가 오히려 코드량을 늘린다.

### actor 격리

`BrieflyAPI.shared`를 `actor`로 선언하면 내부 상태(session, baseURL)에 대한 동시 접근이 Swift 컴파일러 수준에서 금지된다. `@MainActor`나 `DispatchQueue` 수동 관리 없이 Share Extension의 백그라운드 Task에서도 안전하게 호출 가능.

### `#if DEBUG` URL 분리

iOS 앱은 `.env` 파일 로딩 메커니즘이 없다. `#if DEBUG` 조건부 컴파일은:
- Xcode의 Debug/Release 스킴과 1:1 매핑
- 실수로 프로덕션 빌드에 localhost URL이 포함되는 경우를 컴파일 타임에 방지
- CI 빌드(Release 구성)가 자동으로 실제 서버 URL을 사용

### ATS localhost 예외

`NSAllowsArbitraryLoads = false`를 유지하면서 `NSExceptionDomains` → `localhost`만 HTTP를 허용한다. 이 방식은:
- App Store 심사 통과 기준을 충족 (`NSAllowsArbitraryLoads = true`는 심사 시 설명 필요)
- Release 빌드에서는 `baseURL`이 HTTPS를 사용하므로 ATS 예외가 실질적으로 동작하지 않음

## Alternatives Considered

| Option | 기각 이유 |
|--------|----------|
| Alamofire + Router | 4개 엔드포인트에 과잉 추상화. SPM 의존성 추가. |
| Moya | Target Membership이 2개인 Extension 환경에서 세팅 복잡도 증가. |
| `class` (non-actor) + DispatchQueue | actor isolation이 컴파일러 보장을 주는 반면, DispatchQueue는 런타임 오류 가능. |
| `@EnvironmentObject`로 주입 | Share Extension은 SwiftUI EnvironmentObject 지원 안 함. `shared` singleton이 양쪽 타겟 모두에서 동일하게 동작. |
| `.xcconfig`로 URL 분리 | `#if DEBUG`보다 설정 파일 항목 추가 필요. 현재 규모에서 불필요. |

## Consequences

**Positive:**
- 서드파티 의존성 없음 — SwiftPM에 항목 추가 불필요, Extension 크기 영향 없음
- actor + async/await로 스레드 안전성이 컴파일 타임에 검증됨
- `post<B, R>()` 단일 헬퍼로 모든 엔드포인트가 동일한 에러 처리 경로를 따름

**Negative / trade-offs:**
- Interceptor/Retry 로직(토큰 만료 시 자동 refresh)을 직접 구현해야 함 (→ IOS-004로 분리 예정)
- Multipart/form-data, 파일 업로드가 필요해질 경우 URLSession API가 Alamofire보다 verbose

## Related

- Specs: `docs/specs/IOS-001.md`
- ADRs: `ARCH-017` (iOS 인증 방식), `ARCH-014` (multi-provider identity)
- 구현 파일: `Briefly/Briefly/Services/BrieflyAPI.swift`, `Briefly/Briefly/Services/AuthTokenStore.swift`

## Revision History

| Version | Date | Changes | Commit |
|---------|------|---------|--------|
| 1.0.0 | 2026-04-30 | 최초 결정 | suyoung-v1 |

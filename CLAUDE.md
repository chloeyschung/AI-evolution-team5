# Briefly — Project Configuration

## Project
- **앱명:** Briefly (iOS)
- **브랜치 전략:** `main` (기준), `prototype-1` (현재 개발 브랜치)
- **계획 파일:** `docs/plan.md`

## gstack Skills

This project uses [gstack](https://github.com/garrytan/gstack) — AI-powered software factory skills.

Use `/browse` for all web browsing tasks instead of built-in browser tools.

### 스프린트 흐름

```
/investigate  →  /autoplan  →  (구현)  →  /review  →  /qa  →  /ship  →  /retro
   Think           Plan         Build       Review     Test     Ship    Reflect
```

### Think / 분석

| 커맨드 | 설명 |
|--------|------|
| `/investigate` | 버그·문제 원인 추적. 4단계 자동 분석: 증상 수집 → 패턴 분석 → 가설 검증 → 수정 구현. |
| `/health` | 프로젝트 상태 진단. 빌드 오류, 테스트 실패, 의존성 문제 등 전반적인 건강 상태 체크. |

### Plan / 기획·설계

| 커맨드 | 설명 |
|--------|------|
| `/autoplan` | 자동 풀 리뷰 파이프라인. CEO → 디자인 → 엔지니어링 → DX 순으로 자동 실행. 한 번에 4가지 관점의 리뷰. |
| `/plan-ceo-review` | CEO 관점 전략 검토. 제품 방향, 비즈니스 모델, 아키텍처, 보안, 성장 궤도 등 11개 섹션 평가. |
| `/plan-eng-review` | 엔지니어링 아키텍처 검토. 코드 품질, 성능, 확장성, 테스트 커버리지, 배포 전략 검토. |
| `/plan-design-review` | 디자인 시스템 감사. UI 일관성, 접근성, 컴포넌트 구조 리뷰. |
| `/plan-devex-review` | 개발자 경험 평가. 빌드 속도, 디버깅 편의성, 문서화 수준 평가. |
| `/office-hours` | YC 오피스 아워 시뮬레이션. 스타트업 진단 — "Garry Tan이 우리 제품을 보면 뭐라고 할까?" 형태. |

### Build / 디자인·구현 보조

| 커맨드 | 설명 |
|--------|------|
| `/design-consultation` | 디자인 시스템 설계. 색상, 타이포, 컴포넌트 체계를 처음부터 만들어줌. |
| `/design-review` | 디자인 감사 + 자동 수정. 현재 UI 코드를 분석해 개선점을 찾고 직접 고쳐줌. |
| `/design-shotgun` | 디자인 아이디어 탐색. 여러 시각적 방향을 동시에 제안. |
| `/design-html` | HTML 프로토타입 생성. 빠르게 UI를 HTML로 만들어볼 때 사용. |

### Review / 코드 리뷰

| 커맨드 | 설명 |
|--------|------|
| `/review` | PR 올리기 전 전문가 리뷰. 테스트·보안·성능·유지보수성 등 7개 전문가 관점에서 병렬 분석. |
| `/codex` | 멀티 AI 검증. OpenAI Codex에게 세컨드 오피니언을 받음. 중요한 결정 전 교차 검증용. |

### Test / 테스트

| 커맨드 | 설명 |
|--------|------|
| `/qa` | 자동 QA + 수정. 3단계(quick / standard / exhaustive) 테스트 실행 후 버그 자동 수정. |
| `/qa-only` | 리포트만. `/qa`와 같지만 수정은 하지 않고 문제 목록만 보고. |
| `/benchmark` | 성능 회귀 감지. 이전 빌드 대비 성능 저하 여부 측정. |

### Ship / 배포

| 커맨드 | 설명 |
|--------|------|
| `/ship` | 완전 자동 배포 워크플로. 리뷰 → 테스트 → 버전 범프 → 체인지로그 → 커밋 → 푸시 → PR 생성까지 한 번에. |
| `/canary` | 배포 후 모니터링. 배포 직후 에러율, 응답 시간 감시 및 롤백 여부 판단. |

### Reflect / 회고·유틸

| 커맨드 | 설명 |
|--------|------|
| `/retro` | 스프린트 회고. 무엇이 잘됐고 무엇이 문제였는지 분석, `.context/retros/`에 저장. |
| `/browse` | 헤드리스 브라우저. Chromium 조작으로 웹사이트 탐색, 스크린샷, 데이터 추출. |

---

## Development (iOS)

- **Language:** Swift / SwiftUI
- **Min Target:** iOS 16.0
- **Key targets:** `Briefly` (main app), `BrieflyShareExtension` (Share Extension)
- **App Group:** `group.com.briefly.shared`
- **Build:** Xcode

## Progress Tracking

모든 기능 진행 상황은 `docs/plan.md`에서 관리. 작업 후 체크리스트와 진행 로그를 업데이트.

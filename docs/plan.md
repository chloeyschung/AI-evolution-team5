<!-- /autoplan restore point: /Users/melkwon-imac/.gstack/projects/chloeyschung-AI-evolution-team5/prototype-1-autoplan-restore-20260410-215542.md -->
# Briefly — Prototype-1 개발 계획

**브랜치:** `prototype-1`  
**목표:** 핵심 기능 3가지를 검증할 수 있는 iOS 앱 프로토타입 제작  
**플랫폼:** iOS (Swift / SwiftUI)

---

## 핵심 기능 범위 (Prototype-1 Scope)

| 우선순위 | 기능 | 설명 | 상태 |
|----------|------|------|------|
| 1 | **외부 정보 저장** | iOS Share Extension으로 Safari 등 외부 앱에서 링크 저장 | 🔲 진행 예정 |
| 2 | **간결 요약** | 저장된 URL의 내용을 AI로 3줄 요약 | 🔲 미시작 |
| 3 | **Swipe UX** | 요약 카드 스와이프(Keep / Discard) | 🔲 미시작 |

---

## Phase 1 — 외부 정보 저장 (Share Extension)

### 개요
사용자가 Safari나 다른 앱에서 링크를 보다가 iOS 기본 공유 시트(Share Sheet)를 열면,
"Briefly" 앱이 목록에 표시되고, 탭 시 해당 URL이 앱에 저장되는 흐름.

### 기술 구조

```
[Safari / 외부앱]
      ↓ (공유하기 버튼)
[iOS Share Sheet]
      ↓ (Briefly 선택)
[Share Extension Target]  ← NSExtension, NSExtensionActivationRule
      ↓ (URL 추출 + App Group UserDefaults에 저장)
[Briefly 메인 앱]  ← App Group으로 데이터 공유
      ↓
[저장 목록 화면]
```

### 구현 단계

#### Step 1. Xcode 프로젝트 생성
- [ ] 프로젝트명: `Briefly`
- [ ] 번들 ID: `com.briefly.app`
- [ ] 타겟: iOS 16.0+
- [ ] UI 프레임워크: SwiftUI

#### Step 2. Share Extension 타겟 추가
- [ ] File > New > Target > Share Extension 추가
- [ ] 타겟명: `BrieflyShareExtension`
- [ ] App Group 설정: `group.com.briefly.shared`
  - 메인 앱 + Share Extension 양쪽 모두 App Group 활성화
- [ ] `Info.plist` — NSExtensionActivationRule 설정 (URL 타입만 허용)

#### Step 3. Share Extension 로직 구현
- [ ] `ShareViewController.swift` 작성
  - 공유된 아이템에서 URL 추출
  - App Group UserDefaults에 URL 배열로 저장
  - 저장 완료 후 Extension 닫기
- [ ] UI: 간단한 "Briefly에 저장됨" 확인 뷰 (SwiftUI or UIKit)

#### Step 4. 메인 앱 저장 목록 화면
- [ ] `ContentView.swift` — App Group UserDefaults에서 URL 목록 로드
- [ ] `SavedItemsView.swift` — 저장된 링크 리스트 표시
- [ ] 앱이 포그라운드로 돌아올 때 목록 자동 갱신 (`scenePhase` 활용)

#### Step 5. 데이터 모델
- [ ] `SavedItem` 구조체: `id`, `url`, `title`, `savedAt`, `status(unread/read/discarded)`
- [ ] 저장소: `App Group UserDefaults` (MVP), 이후 CoreData 또는 SwiftData로 마이그레이션 고려

### 완료 기준 (Definition of Done)
- Safari에서 링크 공유 → Briefly 선택 → 앱 열면 목록에 보임

---

## Phase 2 — 간결 요약 (AI Summary) [미시작]

### 개요
저장된 URL의 웹 콘텐츠를 크롤링하고 Claude API (또는 OpenAI)로 3줄 요약 생성.

### 예정 기술 스택
- URL 콘텐츠 파싱: `URLSession` + HTML 파서 (SwiftSoup)
- AI 요약: Claude API (`claude-haiku-4-5` — 빠르고 저렴)
- 비동기 처리: `async/await`

---

## Phase 3 — Swipe UX [미시작]

### 개요
요약된 카드를 Tinder 스타일 스와이프로 분류.

### 예정 기술 스택
- SwiftUI `DragGesture`로 카드 애니메이션 구현
- Right → Keep (태그 저장), Left → Discard (아카이브)

---

## 진행 로그

| 날짜 | 업데이트 내용 |
|------|--------------|
| 2026-04-10 | plan.md 초안 작성. prototype-1 브랜치 생성. Phase 1 설계 완료. |
| 2026-04-10 | /autoplan 실행. 팀 결정: prototype-1은 Phase 1(Share Extension)만 집중. |

---

## /autoplan CEO Review — Phase 1

### 범위 결정 (게이트 통과)
**팀 결정:** prototype-1 = Phase 1(Share Extension) 완성도 집중. Phases 2-3 → 별도 PR.

**근거:** PREMORTEM에서 예언한 "다 만들어야 vs 일단 돌아가게만" 충돌을 예방. Phase 1 완성 후 팀 전체 성취감 → 이후 단계 자신감.

---

### Step 0A: Premise Challenge

| 전제 | 판정 | 비고 |
|------|------|------|
| iOS Share Extension이 첫 번째 수집 채널로 적합하다 | ✅ 유효 | iOS 표준 패턴, 검증된 UX |
| 3줄 AI 요약이 올바른 포맷이다 | ⚠️ 미검증 | 인터뷰 없이 가정 |
| App Group + UserDefaults로 MVP 충분 | ✅ 유효 | MVP 단계 적절 |
| Swipe UX가 지식 소화에 맞다 | ⚠️ 미검증 | Phase 3에서 검증 예정 |
| Claude Haiku가 속도/비용 대비 적합 | ✅ 유효 | Phase 2 관련, 현재 범위 외 |
| Share Extension만으로 prototype 검증 가능 | ✅ 유효 | 팀 결정으로 확정 |

**핵심 챌린지 (서브에이전트 발견):** "저장 문제"가 아니라 "선택 문제"일 수 있음. 진짜 차별화는 저장 시점에 1줄 미리보기를 제공하는 것 — Phase 1 Share Extension 안에서 구현 가능한 아이디어.

---

### Step 0B: 기존 코드 레버리지

현재 Swift 코드 없음 — 완전 greenfield 프로젝트. 재사용 가능한 기존 컴포넌트 없음.

iOS SDK에서 활용:
- `NSExtensionItem` — URL 추출 (표준 API)
- `UserDefaults(suiteName:)` — App Group 공유 저장소
- `SwiftUI.List` — URL 목록 표시
- `scenePhase` — 앱 포그라운드 복귀 시 갱신

---

### Step 0C: Dream State Diagram

```
CURRENT                    PHASE 1 (이번)           12개월 목표
────────                   ──────────────           ─────────────
링크 저장 = 없음 →           Share Extension          Share → AI 요약 → Swipe
정보 죄책감 높음               URL 저장 동작             → Keep/Discard
                           팀 모두 동작하는            → 리텐션 알림
Pocket/Instapaper는          앱 있음                   → 브라우저 익스텐션
이미 이걸 다 함             정보 묘지 1.0              → 월 구독 모델
                           (소비 UX 아직 없음)
```

**Delta 분석:** Phase 1 후에도 Briefly는 Pocket의 기능 서브셋. 차별화(스와이프 + AI)는 Phase 2-3에서 나옴. Phase 1은 기반 검증.

---

### Step 0C-bis: 구현 대안

| 접근법 | 노력(CC) | 위험도 | 장점 | 단점 |
|--------|----------|--------|------|------|
| A) Share Extension + UserDefaults (현재 계획) | 1일 | 낮음 | 표준, 문서화 잘됨 | 1MB 한도, 마이그레이션 없음 |
| B) Share Extension + SwiftData | 2일 | 중간 | 진짜 영속성, 마이그레이션 | iOS 17+ 필요 (vs 16+) |
| C) Safari Extension (no app switching) | 2일 | 중간 | 마찰 더 낮음 | Safari 전용, 범용성 부족 |

**결정 (auto-P5):** A 유지. 계획이 이미 최적 선택.

---

### Step 0D-F: 모드 확정

모드: **HOLD SCOPE** (Phase 1만). Phases 2-3 → TODOS.md로 이동.

---

### Error & Rescue Registry

| # | 에러 상황 | 심각도 | 현재 계획 | 해결책 |
|---|----------|--------|-----------|--------|
| E1 | NSExtensionItem에서 URL 추출 실패 | P1 | 미정의 | try-catch + "URL을 찾을 수 없습니다" 메시지 |
| E2 | App Group UserDefaults 쓰기 실패 | P1 | 미정의 | 실패 시 로컬 임시 저장 + 다음 앱 실행 시 재시도 |
| E3 | Extension이 URL 아닌 콘텐츠에서 실행 | P2 | NSExtensionActivationRule로 필터링 예정 | Rule 정확히 지정: `public.url` 타입만 |
| E4 | 메인 앱이 빈/손상된 UserDefaults 읽기 | P2 | 미정의 | Optional 처리 + 빈 상태 UI |
| E5 | 연속 빠른 공유 시 race condition | P3 | 미정의 | DispatchQueue 또는 atomic write |
| E6 | 개발자 계정 없어서 Extension 테스트 불가 | P1 (팀 운영) | 미정의 | 팀 내 개발자 계정 보유자 확인 필수 |

---

### Failure Modes Registry

| 실패 | 가능성 | 영향 | 계획 포함? |
|------|--------|------|-----------|
| App Group entitlement 미설정 | 높음 | Extension 아예 안 나타남 | ❌ 미언급 |
| NSExtensionActivationRule 미설정 | 높음 | 모든 공유에서 Extension 노출 | ❌ 미언급 |
| UserDefaults flush 타이밍 이슈 | 중간 | 저장된 URL이 앱에서 안 보임 | ❌ 미언급 |
| SavedItem.title 없이 URL만 표시 | 높음 | 목록이 URL 나열 — UX 극히 불량 | ❌ 미언급 |
| Apple Developer 계정 없음 | 팀 의존 | Phase 1 전체 블로킹 | ❌ 미언급 |
| 공유 후 앱 열기 경로 없음 | 높음 | 저장했지만 확인 방법 불명확 | ❌ 미언급 |

---

### CLAUDE 서브에이전트 CEO 리뷰 (독립 분석)

**CLAUDE SUBAGENT (CEO — strategic independence)**

7개 주요 발견:

1. **[HIGH] 문제 프레임 오류:** 진짜 문제는 "저장"이 아니라 "주의 분산과 죄책감 누적". 10x 리프레임: 저장 시점에 Share Extension 내에서 1문장 AI 미리보기 제공 → 저장 여부 결정 지원.

2. **[HIGH] 검증되지 않은 전제:** 3줄 요약, 사용자가 앱을 다시 열 것이라는 가정 — 인터뷰 없이 가정됨. 5명 인터뷰 권장.

3. **[CRITICAL] 6개월 후 후회 시나리오:** Readwise Reader, Matter, Perplexity가 이미 저장+AI 요약을 제공. Briefly의 유일한 차별화인 Swipe UX(Phase 3)가 뒤로 밀려남. 스와이프를 브랜드 정체성으로 앞세워야 함.

4. **[MEDIUM] 대안 분석 부재:** Safari Extension(앱 전환 불필요), Shortcuts + Notion 자동화 등 미검토.

5. **[HIGH] 경쟁 위험:** Readwise Reader는 Share Extension + AI 요약 + 스와이프 분류를 이미 제공. Briefly가 Readwise보다 나은 점 1가지를 지금 정의하지 않으면 6개월 후 실패.

6. **[CRITICAL] Phase 1이 2시간 안에 블로킹될 3가지:**
   - Apple 유료 개발자 계정 없으면 Share Extension 디바이스 테스트 불가
   - `NSExtensionActivationRule` 미지정 → Extension이 사파리 공유시트에 안 보이거나 어디서나 나타남
   - UserDefaults 비동기 flush 타이밍 이슈 → 저장됐지만 앱에서 안 보이는 현상

7. **[HIGH] 성공 지표 없음:** "앱이 열리고 목록 보임"은 빌드 기준이지 제품 기준이 아님. 측정 가능한 목표 정의 필요 (예: "5명이 1주일 안에 각 3개 이상 링크 저장").

---

### CEO DUAL VOICES — 합의 테이블

```
CEO DUAL VOICES — CONSENSUS TABLE:
═══════════════════════════════════════════════════════════════
  항목                                    Claude  Codex  합의
  ─────────────────────────────────────── ─────── ─────── ────
  1. 전제 유효성?                          부분    N/A    부분
  2. 올바른 문제를 풀고 있나?              부분    N/A    부분
  3. 범위 설정 적절?                       유효    N/A    유효
  4. 대안 충분히 탐색?                     부족    N/A    부족
  5. 경쟁/시장 위험 커버?                  부족    N/A    부족
  6. 6개월 궤도 탄탄?                      위험    N/A    위험
═══════════════════════════════════════════════════════════════
모드: [subagent-only] — Codex CLI 미설치
```

---

### NOT in Scope (prototype-1)

- Phase 2 (AI 요약, Claude API 연동)
- Phase 3 (Swipe UX, DragGesture)
- 브라우저 익스텐션
- macOS/iPadOS 지원
- CoreData/SwiftData 마이그레이션
- 사용자 인증/계정
- 개인화 추천, 스마트 리마인더
- 성공 지표 측정 인프라

---

### CEO Completion Summary

| 항목 | 평가 |
|------|------|
| 문제-솔루션 핏 | 7/10 — 문제 실재, 하지만 프레임 미세 조정 필요 |
| 범위 설정 | 8/10 — Phase 1만 집중 결정 후 적절 |
| 경쟁 분석 | 4/10 — Readwise 대비 차별화 정의 없음 |
| 실행 가능성 | 6/10 — 개발자 계정 이슈가 즉시 블로커 |
| 성공 지표 | 2/10 — 정량 목표 없음 |
| 팀 리스크 | 5/10 — PREMORTEM 예언 중 일부가 이미 구조 안에 있음 |

**핵심 액션 (Phase 1 전 해결):**
1. Apple Developer 계정 보유 팀원 확인 (블로커)
2. NSExtensionActivationRule PLIST 정확히 설정
3. Phase 1 완료 기준에 "URL 제목 표시" 추가
4. 성공 지표 1개 정의 (예: "팀원 4명 모두 3개씩 링크 저장")

---

---

## /autoplan Design Review — Phase 2

### Step 0: 디자인 완성도 평가

**초기 점수: 2/10** — UI가 언급만 됨. 행 해부학, 빈 상태, 에러 상태, 탭 동작 미정의.
**DESIGN.md:** 없음 (권장: 구현 전 `/design-consultation` 실행)
**Design binary:** 런타임 실패 (API 설정 미완) → 텍스트 기반 리뷰로 대체

---

### CLAUDE 서브에이전트 Design 리뷰

**CLAUDE SUBAGENT (design — independent review)**

| 발견 | 심각도 | 수정 사항 |
|------|--------|-----------|
| 목록 행이 raw URL — 읽기 불가 | Critical | 행: 제목(1줄) + 도메인만(medium.com) + 상대시간(2h ago) + 읽음 상태 점 |
| App Group 실패 시 에러 경로 미정의 | Critical | `UserDefaults(suiteName:) == nil` 시 에러 배너 + 콘솔 로그, 저장 무시 금지 |
| 빈 상태 비주얼/카피 미정의 | High | 빈 상태: 일러스트레이션 + "Safari에서 링크를 공유해보세요" + 방법 안내 |
| 행 탭 동작 미정의 | High | 탭 → Safari에서 URL 열기 (`.open(url)`) 명시 필요 |
| Share Extension 신뢰 순간 미정의 | High | `.presentationDetents([.height(200)])`, 1.5초 자동 닫기, 체크마크 SF Symbol 애니, 실패 메시지 |
| NavigationStack vs NavigationView 미지정 | Medium | iOS 16+ → `NavigationStack` 사용 명시 |
| 정렬 순서 미지정 | Medium | 최신순(savedAt 내림차순) 명시 |
| Pull-to-refresh 미언급 | Medium | `.refreshable` 수정자 추가 — 유저가 당겨서 새로고침 기대 |
| 중복 URL 저장 동작 | Medium | 중복 시: 기존 항목 업데이트 (savedAt 갱신) vs 무시 — 정의 필요 |

**DESIGN DUAL VOICES:**
```
═══════════════════════════════════════════════════════════════
  항목                              Claude  Codex  합의
  ────────────────────────────────── ─────── ─────── ────
  1. 정보 계층 정의됨?              No      N/A    No
  2. 상태들 완전히 지정됨?          No      N/A    No
  3. 사용자 여정 명확?              부분    N/A    부분
  4. 구체성 충분?                   No      N/A    No
  5. 신뢰 순간 설계됨?              No      N/A    No
  6. 접근성 명시?                   No      N/A    No
  7. 반응형/적응형 고려?            N/A     N/A    N/A (iOS전용)
═══════════════════════════════════════════════════════════════
모드: [subagent-only]
```

---

### 계획 업데이트 — Phase 1 UI 명세 보강

#### Share Extension UI 명세 (Step 3 보완)

```
ShareViewController 확인 뷰:
- .presentationDetents([.height(200)])
- 체크마크 SF Symbol (checkmark.circle.fill) 애니메이션
- 저장된 URL 도메인 표시 (예: "medium.com에서 저장됨")
- 1.5초 후 자동 닫기 (DispatchQueue.main.asyncAfter)
- 실패 시: "저장 실패 — Briefly 앱을 열어 재시도해주세요"
```

#### SavedItemsView 명세 (Step 4 보완)

```
행(Row) 해부학:
- Leading: 읽음 상태 점 (unread = filled blue dot, read = none)
- Primary: title (1줄 truncated, 없으면 URL 표시)
- Secondary: domain only (예: medium.com) + " · " + 상대시간 (예: 2시간 전)
- Trailing: 공유 아이콘 (선택사항 Phase 1)

행 탭 동작:
- URL을 Safari에서 열기: UIApplication.shared.open(url)
- status → .read 로 변경

빈 상태:
- 아이콘: link.circle SF Symbol (large)
- 제목: "아직 저장된 링크가 없어요"
- 설명: "Safari에서 기사를 보다가 공유 버튼을 탭하고 Briefly를 선택해보세요"

정렬: savedAt 내림차순 (최신 저장 → 상단)
새로고침: .refreshable { viewModel.loadItems() }
Navigation: NavigationStack (iOS 16+)
중복 URL: 기존 항목 savedAt 업데이트 (중복 저장 허용 않음)
```

#### 에러 상태 명세

```
App Group 실패:
- UserDefaults(suiteName: "group.com.briefly.shared") == nil
- → 배너: "동기화 문제 발생. 앱 설정을 확인해주세요."
- → console.log 출력 (디버깅용)
- → 저장 무시 (크래시 없음)
```

---

### Design 점수 (7개 차원)

| 차원 | 초기 | 목표 | 핵심 갭 |
|------|------|------|---------|
| 1. 정보 계층 | 1/10 | 8/10 | 행 해부학 정의됨 (위 명세) |
| 2. 빈/에러 상태 | 1/10 | 8/10 | 빈 상태 + App Group 실패 정의됨 |
| 3. 사용자 여정 | 3/10 | 7/10 | 탭 동작 정의됨 |
| 4. 신뢰 순간 | 2/10 | 8/10 | Share Extension 애니 + 자동닫기 |
| 5. 구체성 | 2/10 | 8/10 | Nav, 정렬, 새로고침 모두 정의됨 |
| 6. 접근성 | 0/10 | 6/10 | SF Symbol 사용 (자동 Dynamic Type) |
| 7. 반응형 | N/A | N/A | iOS 전용 — iPad 지원 범위 외 |

**Design 리뷰 후 점수: 7/10** (명세 보완 완료)

---

---

## /autoplan Engineering Review — Phase 3

### Step 0: 범위 챌린지

**파일 수:** 6개 코드 파일 (8개 미만 — 복잡도 문제 없음)
**새 타입:** SavedItem, StorageService, ShareViewController, SavedItemsView = 4개 (2개 초과지만 greenfield 앱에 정상)
**결론:** 범위 축소 불필요. 이미 최소 구현.

**Distribution:** iOS 앱 새 아티팩트 → TestFlight/Ad-hoc 배포 미언급. **블로커 플래그:** 팀원 디바이스 테스트에 Apple Developer 계정 필수.

**기존 코드:** 없음 (greenfield). 모든 컴포넌트 신규 구현.

---

### Section 1: Architecture

**아키텍처 다이어그램:**

```
[Safari / 외부앱]
      │ 공유 버튼
      ↓
[iOS Share Sheet]
      │ Briefly 선택
      ↓
┌─────────────────────────────────┐
│  BrieflyShareExtension target   │
│  ShareViewController.swift      │
│    │ NSExtensionItem 파싱        │
│    │ URL 추출 (async loadItem)   │
│    │ JSONEncoder().encode([])    │
│    ↓                            │
│  UserDefaults(suiteName:        │
│  "group.com.briefly.shared")    │
│  .set(data, forKey:"inbox")     │  ← inbox/drain 패턴
│    │ completeRequest()           │
└─────────────────────────────────┘
             │
             ↓ App Group 공유 컨테이너
┌─────────────────────────────────┐
│  Briefly 메인 앱 target          │
│  BrieflyApp.swift               │
│  ContentView.swift              │
│  SavedItemsView.swift           │
│    │ .onChange(scenePhase == .active)
│    │ StorageService.loadItems()  │
│    │ drain inbox + merge main    │
│    ↓                            │
│  [SavedItem] 목록 표시           │
│    │ 행 탭                       │
│    ↓                            │
│  UIApplication.shared.open(url) │
└─────────────────────────────────┘
```

**아키텍처 이슈:**

| 이슈 | 심각도 | 신뢰도 | 수정 |
|------|--------|--------|------|
| SavedItem.swift를 양쪽 타겟이 모두 필요한데 공유 방법 미지정 | P1 | 9/10 | 두 타겟 모두에 파일 추가 (Xcode → Target Membership 체크), 또는 BrieflyCore shared framework |
| 동시 공유 시 race condition (read-modify-write) | P1 | 8/10 | inbox/drain 패턴: Extension은 "inbox" 키에 append만, 앱이 main에 merge |
| scenePhase 트리거: `.foreground` vs `.active` | P2 | 9/10 | `.active` 사용 (`.foreground`는 화면 보이기 전에 발생) |
| URL 추출이 동기 가정 — 실제 async | P1 | 9/10 | `provider.loadItem(forTypeIdentifier:)` 는 completion-based async |
| Extension이 completeRequest 없으면 hang | P1 | 9/10 | 성공/실패 모두 `extensionContext?.completeRequest(returningItems: [])` 필수 |

---

### Section 2: Code Quality

**구체적 구현 명세 추가 (계획 보완):**

**SavedItem.swift:**
```swift
// 두 타겟(Briefly + BrieflyShareExtension) 모두 Target Membership 설정
struct SavedItem: Codable, Identifiable {
    let id: UUID
    let url: URL
    var title: String?
    let savedAt: Date
    var status: Status
    
    enum Status: String, Codable {
        case unread, read, discarded
    }
    
    init(url: URL, title: String? = nil) {
        self.id = UUID()
        self.url = url
        self.title = title
        self.savedAt = Date()
        self.status = .unread
    }
}
```

**StorageService.swift — inbox/drain 패턴:**
```swift
// inbox 키: Extension이 여기에만 씀
// savedItems 키: 앱이 merge 후 여기서 읽음
static let inboxKey = "brieflyInbox"
static let mainKey = "savedItems"

// Extension: inbox에 append
func appendToInbox(_ item: SavedItem) throws {
    var inbox = loadFromKey(inboxKey)
    inbox.append(item)
    try save(inbox, forKey: inboxKey)
}

// 앱: drain inbox → merge → main에 저장
func drainInbox() -> [SavedItem] {
    let inbox = loadFromKey(inboxKey)
    var main = loadFromKey(mainKey)
    // 중복 제거: URL 기준
    let existingURLs = Set(main.map(\.url))
    let newItems = inbox.filter { !existingURLs.contains($0.url) }
    main.append(contentsOf: newItems)
    main.sort { $0.savedAt > $1.savedAt }
    try? save(main, forKey: mainKey)
    defaults.removeObject(forKey: inboxKey)
    return main
}
```

**NSExtensionActivationRule (Info.plist):**
```xml
<key>NSExtensionActivationRule</key>
<dict>
    <key>NSExtensionActivationSupportsWebURLWithMaxCount</key>
    <integer>1</integer>
</dict>
```

**URL 추출 (async 패턴):**
```swift
guard let item = extensionContext?.inputItems.first as? NSExtensionItem,
      let provider = item.attachments?.first,
      provider.hasItemConformingToTypeIdentifier(UTType.url.identifier) else {
    extensionContext?.completeRequest(returningItems: [])
    return
}
provider.loadItem(forTypeIdentifier: UTType.url.identifier) { [weak self] urlItem, error in
    guard let url = urlItem as? URL else {
        self?.extensionContext?.completeRequest(returningItems: [])
        return
    }
    let item = SavedItem(url: url)
    try? self?.storageService.appendToInbox(item)
    DispatchQueue.main.async {
        self?.extensionContext?.completeRequest(returningItems: [])
    }
}
```

**코드 품질 이슈:**

| 이슈 | 심각도 | 신뢰도 | 수정 |
|------|--------|--------|------|
| JSON 직렬화 방식 미지정 | P1 | 9/10 | JSONEncoder + Codable (위 명세) |
| completeRequest 누락 시 Extension hang | P1 | 9/10 | 성공/실패 모든 경로에 completeRequest 호출 |
| URL 추출 completion 누락 | P1 | 9/10 | async loadItem 패턴 사용 |

---

### Section 3: Test Review

**테스트 프레임워크:** CLAUDE.md에 Testing 섹션 없음. iOS → XCTest + XCUITest 사용.

**Coverage Diagram:**

```
CODE PATH COVERAGE
===========================
[+] SavedItem.swift
    ├── [GAP] init(url:title:) — id/savedAt 자동 생성 검증
    ├── [GAP] Codable 직렬화/역직렬화 round-trip
    └── [GAP] status enum 전환

[+] StorageService.swift
    ├── [GAP] appendToInbox() — 정상 저장
    ├── [GAP] appendToInbox() — App Group 미사용 시 에러 처리
    ├── [GAP] drainInbox() — inbox → main merge
    ├── [GAP] drainInbox() — 중복 URL 제거
    ├── [GAP] drainInbox() — 빈 inbox
    └── [GAP] loadFromKey() — 손상된 Data 역직렬화

[+] ShareViewController.swift
    ├── [GAP] URL 추출 성공 경로
    ├── [GAP] URL 추출 실패 (non-URL 콘텐츠)
    ├── [GAP] NSExtensionItem nil
    └── [GAP] completeRequest 호출 검증

USER FLOW COVERAGE
===========================
[+] Safari → Share Extension → App 목록
    ├── [GAP] [→E2E] 정상 흐름 전체
    ├── [GAP] URL 공유 후 앱 포그라운드 전환 시 목록 갱신
    └── [GAP] 중복 URL 두 번 공유 시 목록에 1개만 표시

[+] SavedItemsView
    ├── [GAP] 빈 상태 표시
    ├── [GAP] 항목 탭 시 Safari 열림
    ├── [GAP] pull-to-refresh
    └── [GAP] 항목 정렬 (최신순)

─────────────────────────────────
COVERAGE: 0/16 경로 테스트됨 (0%)
  Code paths: 0/11 (0%)
  User flows: 0/5 (0%)
GAPS: 16개 경로 테스트 없음 (1개 E2E 권장)
─────────────────────────────────
```

**테스트 요구사항 (계획에 추가):**

필수 Unit Tests (`BrieflyTests/`):
1. `testSavedItemCodable` — JSON round-trip
2. `testStorageServiceAppend` — inbox에 저장됨
3. `testStorageServiceDrain` — merge + 중복 제거
4. `testStorageServiceEmpty` — 빈 inbox drain
5. `testShareViewControllerURL` — URL 추출 성공
6. `testShareViewControllerNonURL` — 실패 경로에서 completeRequest 호출

권장 Integration Test:
- `testFullSaveFlow` [→E2E/Integration]: Extension이 저장한 URL이 앱에서 보이는지

---

### Section 4: Performance

**메모리:** Share Extension 120MB 한도. JSON 직렬화는 수백KB 수준 — 안전.
**UserDefaults 크기:** URL당 ~500B × 1000개 = ~500KB. 한도(4MB) 내 안전.
**Main Thread:** UserDefaults 읽기는 빠름. scenePhase.active 트리거는 메인 스레드 — 대용량 데이터는 백그라운드 큐로 이동 권장 (Phase 1 MVP는 허용).

**분석:** 성능 위험 없음 — MVP 데이터 규모에서 UserDefaults 접근은 ms 단위.

---

### ENG DUAL VOICES — 합의 테이블

```
ENG DUAL VOICES — CONSENSUS TABLE:
═══════════════════════════════════════════════════════════════
  항목                              Claude  Codex  합의
  ────────────────────────────────── ─────── ─────── ────
  1. 아키텍처 견고?                  부분    N/A    부분
  2. 테스트 커버리지 충분?            No      N/A    No
  3. 성능 위험 해결?                  Yes     N/A    Yes
  4. 보안 위협 커버?                  부분    N/A    부분
  5. 에러 경로 처리?                  No      N/A    No
  6. 배포 위험 관리?                  No      N/A    No
═══════════════════════════════════════════════════════════════
모드: [subagent-only]
```

**핵심 미해결 이슈 (P1):**
1. SavedItem 타겟 멤버십 설정 미지정 → 빌드 실패
2. async URL 추출 패턴 미지정 → Extension 오동작
3. inbox/drain 패턴 미지정 → race condition
4. completeRequest 미지정 → Extension hang
5. 테스트 0개 → 품질 검증 불가
6. TestFlight 배포 계획 없음 → 팀 디바이스 테스트 불가

---

### NOT in Scope (Engineering)

- Unit test 작성 (계획에 요구사항 추가됨, 구현은 별도)
- TestFlight 배포 자동화
- CI/CD (GitHub Actions)
- CoreData/SwiftData 마이그레이션
- 백그라운드 URLSession (Phase 2)
- CloudKit 동기화

### What Already Exists

- iOS SDK: NSExtensionItem, UserDefaults, SwiftUI, scenePhase, JSONEncoder — 모두 Layer 1 (표준 프레임워크)
- 3rd party 라이브러리 불필요

---

### Eng Completion Summary

| 항목 | 평가 |
|------|------|
| 아키텍처 | 5/10 → 8/10 (inbox/drain 패턴 추가 후) |
| 코드 품질 계획 | 3/10 → 8/10 (구체적 패턴 정의 후) |
| 테스트 커버리지 | 0/10 → 계획 추가됨 (구현은 미완) |
| 보안 | 7/10 — URL만 저장, App Group 격리 |
| 배포 | 2/10 — Developer 계정/TestFlight 계획 없음 |

---

## Decision Audit Trail

| # | Phase | 결정 | 분류 | 원칙 | 근거 | 기각 |
|---|-------|------|------|------|------|------|
| 1 | CEO | Prototype-1 범위를 Phase 1만으로 축소 | 게이트 | 팀 결정 | PREMORTEM 충돌 예방, 성취감 우선 | 3개 동시 진행 |
| 2 | CEO | App Group + UserDefaults 유지 | Mechanical | P5 (명시적) | 표준 패턴, MVP에 적합 | SwiftData(iOS 17+), CloudKit |
| 3 | CEO | Phase 2-3 → TODOS | Mechanical | P3 (실용적) | 범위 집중 | 함께 구현 |
| 4 | Design | 7개 전체 차원 검토 | Mechanical | P1 (완전성) | autoplan은 완전한 검토 기본 | 특정 차원만 |
| 5 | Design | NavigationStack 사용 (iOS 16+) | Mechanical | P5 (명시적) | NavigationView deprecated in 16 | NavigationView |
| 6 | Eng | inbox/drain 패턴 권장 | Taste | P5 (명시적 > 영리함) | race condition 회피, 구현 단순 | 단일 키 read-modify-write |
| 7 | Eng | 테스트 요구사항 계획에 추가 | Mechanical | P1 (완전성) | 0% 커버리지는 허용 불가 | 테스트 없이 진행 |

---

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | issues_open | 팀 리스크, 경쟁 분석 부족, 성공 지표 없음, 개발자 계정 블로커 |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | skipped | Codex CLI 미설치 |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | issues_open | async URL 추출, inbox/drain, completeRequest, 타겟 멤버십, 테스트 0% |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | issues_open | 행 해부학, 빈 상태, 에러 상태, Share Extension 피드백 |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | skipped | DX scope 미감지 (소비자 iOS 앱) |

**VERDICT:** APPROVED — 7개 자동 결정, 1개 User Challenge (팀이 Phase 1만 유지 선택). 구현 전 반드시 P1 이슈 5개 해결.

**즉시 해결 필요 (구현 전):**
1. `SavedItem.swift` — 두 타겟 모두 Target Membership 설정
2. `NSExtensionActivationSupportsWebURLWithMaxCount: 1` Info.plist
3. async `loadItem(forTypeIdentifier:)` 패턴 사용
4. `completeRequest(returningItems: [])` 모든 경로 호출
5. Apple Developer 계정 보유 팀원 확인

---

## 파일 구조 (예정)

```
Briefly/
├── Briefly/                  # 메인 앱 타겟
│   ├── BrieflyApp.swift
│   ├── ContentView.swift
│   ├── Views/
│   │   ├── SavedItemsView.swift
│   │   ├── CardStackView.swift    (Phase 3)
│   │   └── SummaryCardView.swift  (Phase 2)
│   ├── Models/
│   │   └── SavedItem.swift
│   └── Services/
│       ├── StorageService.swift
│       └── SummaryService.swift   (Phase 2)
├── BrieflyShareExtension/    # Share Extension 타겟
│   ├── ShareViewController.swift
│   └── Info.plist
└── docs/
    └── plan.md               # 이 파일
```

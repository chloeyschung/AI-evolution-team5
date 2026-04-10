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

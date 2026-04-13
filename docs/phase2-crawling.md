# Phase 2a — 콘텐츠 크롤링 (Content Fetching)

**목표:** 저장된 URL에서 제목·썸네일·본문을 자동으로 가져와 카드에 실제 데이터를 표시하고, 이후 AI 요약의 입력 소스로 사용한다.

**선행 조건:** Phase 1 완료 (URL 저장 동작 확인)
**후행 작업:** Phase 2b AI 요약 (`phase2-ai-summary.md`)

---

## 1. 가져올 데이터

| 항목 | 소스 | 카드 표시 | AI 요약 입력 |
|------|------|-----------|-------------|
| 제목 | OG `og:title` → `<title>` 폴백 | ✅ | — |
| 썸네일 | OG `og:image` | ✅ | — |
| 짧은 설명 | OG `og:description` | ✅ (fallback) | 보조 |
| 본문 전체 | HTML 파싱 (article/p 태그) | — | ✅ 주 입력 |
| 사이트명 | OG `og:site_name` → 도메인 폴백 | ✅ | — |

---

## 2. 사이트별 가능 범위

| 사이트 유형 | OG 메타데이터 | 본문 전체 | 비고 |
|-------------|--------------|-----------|------|
| 뉴스·블로그 (공개) | ✅ | ✅ | 기본 동작 |
| Reddit | ✅ | ✅ (댓글 제외) | — |
| YouTube | ✅ (썸네일·제목) | ❌ (자막 API 필요) | Phase 2c 검토 |
| Medium (공개글) | ✅ | ✅ | — |
| Medium (유료글) | ✅ | ❌ (paywall) | OG description으로 대체 |
| LinkedIn | ✅ (제한적) | ❌ (JS 렌더링·로그인) | OG description으로 대체 |
| Instagram | ❌ | ❌ | 지원 불가 |

**LinkedIn 우회 전략:** Share Extension이 호출되는 시점(사용자가 이미 로그인 상태)에
`NSExtensionItem.attachments`로 전달되는 텍스트를 함께 캡처. Phase 2c에서 검토.

---

## 3. 기술 스택

```
URLSession (async/await)
    └─ OG 파싱: 정규식 or SwiftSoup (경량)
    └─ 본문 파싱: SwiftSoup (HTML → 텍스트)

SwiftSoup — Swift Package Manager로 추가
    URL: https://github.com/scinfu/SwiftSoup
    버전: 2.7.x
```

---

## 4. 아키텍처

```
[LibraryView / ItemDetailView]
        ↓ item.fetchStatus == .pending
[FetchCoordinator]
        ├─ MetadataService   → OG title, ogImage, description, siteName
        └─ ArticleService    → 본문 텍스트 (공개 사이트만)
        ↓ 결과를 SavedItem에 merge
[StorageService]  → App Group UserDefaults에 저장
        ↓
[UI 자동 갱신]
```

---

## 5. 데이터 모델 변경 (`SavedItem`)

```swift
// 추가 필드
var ogTitle: String?           // 실제 페이지 제목
var ogImageURL: URL?           // 썸네일 URL
var ogDescription: String?     // 짧은 설명 (AI 요약 fallback)
var siteName: String?          // 사이트명 (예: "LinkedIn", "Medium")
var articleText: String?       // 본문 전체 텍스트 (AI 요약 입력)
var fetchStatus: FetchStatus   // 크롤링 상태

enum FetchStatus: String, Codable {
    case pending    // 아직 시도 안 함
    case fetching   // 진행 중
    case done       // 완료
    case failed     // 실패 (OG도 못 가져옴)
    case partial    // OG만 성공, 본문 실패
}
```

**displayTitle 우선순위:** `ogTitle` → `title` → `url.host`

---

## 6. 구현 단계

### Step 1. SwiftSoup SPM 추가
- Xcode → Package Dependencies → `https://github.com/scinfu/SwiftSoup` 추가
- `project.yml`에 패키지 의존성 반영

### Step 2. `MetadataService` 구현
```
Services/MetadataService.swift

func fetchMetadata(for url: URL) async throws -> PageMetadata
    1. URLSession.data(from: url) — User-Agent: iPhone Safari로 설정
    2. HTML String으로 변환
    3. SwiftSoup으로 <meta> 태그 파싱
       - og:title / og:image / og:description / og:site_name
       - 없으면 <title>, <meta name="description"> 폴백
    4. PageMetadata 구조체로 반환
```

### Step 3. `ArticleService` 구현
```
Services/ArticleService.swift

func fetchArticleText(for url: URL) async throws -> String?
    1. URLSession.data(from: url)
    2. SwiftSoup으로 파싱
    3. <article>, <main>, [role="main"] 순서로 탐색
    4. <p> 태그 텍스트 추출 후 join
    5. 빈 결과이면 nil 반환
```

### Step 4. `FetchCoordinator` 구현
```
Services/FetchCoordinator.swift

func fetchIfNeeded(for items: [SavedItem]) async
    - fetchStatus == .pending 인 아이템만 처리
    - 동시 최대 3개 (TaskGroup)
    - 완료 시 StorageService.updateItem() 호출
```

### Step 5. `SavedItem` 모델 업데이트
- 신규 필드 추가
- `displayTitle` 프로퍼티 우선순위 조정
- Codable 자동 유지 (모든 필드 Optional이므로 하위 호환)

### Step 6. UI 연결
- `LibraryCardView`: `AsyncImage(url: item.ogImageURL)` 로 실제 썸네일
- `LibraryCardView`: `item.ogTitle ?? item.displayTitle` 로 실제 제목
- `ItemDetailView`: 동일하게 실제 데이터 표시
- 로딩 중: 현재 placeholder 유지 (`fetchStatus == .fetching`)
- 실패: placeholder 유지 (`fetchStatus == .failed`)

### Step 7. 트리거 시점
```
앱 포그라운드 진입
    → viewModel.reload() (기존)
    → FetchCoordinator.fetchIfNeeded(for: newItems) (추가)
```
> Share Extension에서는 메모리 제한으로 크롤링 금지. 메인 앱에서만 실행.

---

## 7. 에러 처리

| 상황 | 처리 |
|------|------|
| 네트워크 없음 | `fetchStatus = .pending` 유지, 재시도 안 함 (다음 포그라운드 시 재시도) |
| 타임아웃 (5초) | `fetchStatus = .failed`, OG description으로 fallback |
| HTML 파싱 실패 | `fetchStatus = .partial`, OG만 저장 |
| 403/401 응답 | `fetchStatus = .partial`, OG만 시도 |
| 이미지 URL 깨짐 | AsyncImage placeholder 유지 |

---

## 8. 완료 기준 (Definition of Done)

- [ ] 저장된 뉴스·블로그 링크의 실제 제목·썸네일이 카드에 표시됨
- [ ] 저장된 공개 사이트의 본문 텍스트가 `articleText`에 저장됨
- [ ] LinkedIn·Medium: 제목·썸네일은 표시, 본문은 graceful fallback
- [ ] 크롤링 중 앱 반응성 유지 (async/await, 메인 스레드 블로킹 없음)
- [ ] 네트워크 없는 환경에서 크래시 없음

---

## 9. 진행 로그

| 날짜 | 내용 |
|------|------|
| 2026-04-14 | phase2-crawling.md 초안 작성. 아키텍처·단계 확정. |

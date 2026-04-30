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

| 사이트 유형 | OG 메타데이터 | 본문 전체 | 방식 |
|-------------|--------------|-----------|------|
| 뉴스·블로그 (공개) | ✅ | ✅ | URLSession |
| Reddit | ✅ | ✅ (댓글 제외) | URLSession |
| Medium (공개글) | ✅ | ✅ | URLSession |
| Medium (유료글) | ✅ | ✅ (로그인 시) | WKWebView |
| LinkedIn | ✅ | ✅ (로그인 시) | WKWebView |
| YouTube | ✅ (썸네일·제목) | ❌ (자막 API 필요) | URLSession, Phase 2c 검토 |
| Instagram | ✅ (제한적) | ❌ | WKWebView, 로그인 필요 |

### WKWebView + 공유 쿠키 전략

Readwise Reader가 LinkedIn 전체 본문을 가져오는 원리:

```
사용자가 Safari에서 LinkedIn 로그인 (1회)
        ↓
iOS 시스템이 쿠키를 WKWebsiteDataStore.default()에 공유 보관
        ↓
Briefly 앱이 WKWebView(dataStore: .default()) 로 해당 URL 로딩
        ↓
사용자 세션 쿠키로 인증된 상태로 페이지 렌더링
        ↓
JS 완료 후 본문 텍스트 추출
```

**조건:** 사용자가 Safari(또는 인앱 브라우저)로 해당 서비스에 로그인한 적 있을 것.
별도 백엔드 불필요. 클라이언트 단독으로 처리 가능.

---

## 3. 기술 스택

```
1단계: URLSession (async/await) — 빠른 선처리
    └─ OG 파싱: SwiftSoup
    └─ 본문 파싱: SwiftSoup (<article>, <main>, <p> 추출)

2단계: WKWebView + .default() 쿠키 스토어 — JS 렌더링 필요 사이트
    └─ WKNavigationDelegate로 로딩 완료 감지
    └─ evaluateJavaScript()로 본문 텍스트 추출
    └─ 백그라운드 WKWebView (화면에 표시 안 함)

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
        ├─ MetadataService (URLSession)
        │       → OG title, ogImage, description, siteName
        │       → 공개 사이트 본문 텍스트
        │
        └─ (본문 실패 시) WebContentService (WKWebView)
                → 공유 쿠키로 JS 렌더링
                → LinkedIn·Medium 등 인증 필요 사이트 본문
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
    5. 빈 결과이면 nil 반환 → WebContentService로 폴백
```

### Step 3b. `WebContentService` 구현 (JS 렌더링 필요 사이트)
```
Services/WebContentService.swift

func fetchWithWebView(url: URL) async throws -> String?
    1. WKWebView(dataStore: .default()) 생성 (화면 밖에 배치)
    2. url 로드 → WKNavigationDelegate.didFinish 대기
    3. evaluateJavaScript("document.body.innerText") 호출
    4. 텍스트 반환 후 WKWebView 해제
    5. 타임아웃: 10초

적용 대상 도메인: linkedin.com, medium.com, instagram.com 등
판단 기준: ArticleService 결과가 500자 미만이면 자동 폴백
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

- [x] 저장된 뉴스·블로그 링크의 실제 제목·썸네일이 카드에 표시됨
- [x] 저장된 공개 사이트의 본문 텍스트가 `articleText`에 저장됨
- [x] LinkedIn: Safari 로그인 상태 시 전체 본문 추출 성공
- [x] YouTube: OG 제목·썸네일 추출 성공, 설명(ogDescription)을 본문 폴백으로 표시
- [x] 크롤링 중 앱 반응성 유지 (async/await, 메인 스레드 블로킹 없음)
- [x] 네트워크 없는 환경에서 크래시 없음
- [ ] Reddit: 현재 "Please wait for verification" 페이지 반환 → 미해결 (다음 세션)
- [ ] "지금 읽기" 딥링크: 실기기 테스트 필요 (시뮬레이터에서 extensionContext?.open 미지원)

---

## 9. 백엔드 개발자 역할 (Backend Developer Responsibilities)

> 현재 클라이언트 단독(URLSession + WKWebView)으로 구현하지만,
> 백엔드 개발자가 합류하면 아래 서버 측 기능으로 전환해 더 넓은 범위를 커버할 수 있습니다.

### 9-1. 서버 크롤링 API
| 엔드포인트 | 역할 |
|-----------|------|
| `POST /api/fetch-content` | URL을 받아 OG 메타데이터 + 본문 텍스트 반환 |
| `GET /api/fetch-status/{id}` | 비동기 크롤링 완료 여부 폴링 |

Request body:
```json
{ "url": "https://www.linkedin.com/posts/..." }
```
Response body:
```json
{
  "ogTitle": "...",
  "ogImageURL": "https://...",
  "ogDescription": "...",
  "siteName": "LinkedIn",
  "articleText": "본문 전체..."
}
```

### 9-2. 헤드리스 브라우저 크롤링
- **도구:** Playwright(Node.js) 또는 Puppeteer
- **적용 대상:** LinkedIn, YouTube(자막), Instagram, Medium(유료)
- 서버에서 실제 브라우저를 띄워 JS 렌더링 후 본문 추출
- **쿠키 불필요** — 서버 세션 또는 서비스 계정으로 인증

### 9-3. 인증 관리
| 서비스 | 방식 |
|--------|------|
| LinkedIn | OAuth 2.0 (공식 API) 또는 서버 계정 세션 쿠키 |
| YouTube | YouTube Data API v3 (자막: captions.download) |
| Medium | RSS 피드 또는 공식 API |
| Instagram | Meta Graph API (제한적) |

### 9-4. 프록시 / 레이트 리밋 처리
- IP 차단 방지: rotating proxy pool 운영
- 요청 간격 조절 (rate limiting per domain)
- 실패 시 자동 재시도 로직 (exponential backoff)

### 9-5. 클라이언트 전환 시 변경 필요 파일
- `MetadataService.swift` → 서버 API 호출로 교체
- `ArticleService.swift` → 서버 응답 파싱으로 교체
- `WebContentService.swift` → 불필요 (서버가 처리)
- `FetchCoordinator.swift` → 폴링 또는 웹소켓으로 전환

---

## 10. 다음 세션에서 할 일 (Next Steps)

### 2a 잔여 작업
| 우선순위 | 항목 | 설명 |
|---------|------|------|
| 🔴 높음 | Reddit 크롤링 해결 | Reddit이 봇 감지로 verification 페이지 반환. WKWebView + 공유 쿠키 전략으로 전환 또는 User-Agent 튜닝 시도 |
| 🟡 중간 | "지금 읽기" 실기기 테스트 | `extensionContext?.open()` 시뮬레이터 미지원. 실기기에서 Library 탭 + 상세 카드 이동 확인 |
| 🟡 중간 | 재시도 기능 | fetchStatus == .failed 인 아이템을 수동 또는 자동으로 재시도하는 버튼/로직 추가 |
| 🟢 낮음 | 저장된 아이템 삭제 기능 | 카드 스와이프 또는 버튼으로 삭제 (Discard → Archive 이동) |

### 2b 다음 Phase
| 항목 | 설명 |
|------|------|
| Claude API 연동 | `articleText` 또는 `ogDescription`을 입력으로 최대 300자 요약 생성 |
| `phase2-ai-summary.md` 작성 | AI 요약 phase 문서 작성 후 구현 시작 |
| AI 요약 UI | ItemDetailView의 "AI 요약" 섹션에 실제 Claude 요약 결과 표시 |
| 비용 관리 | 캐싱 전략 — 이미 요약된 아이템 재요약 방지 (`aiSummary` 필드 nil 체크) |

---

## 11. 진행 로그

| 날짜 | 내용 |
|------|------|
| 2026-04-14 | phase2-crawling.md 초안 작성. 아키텍처·단계 확정. |
| 2026-04-14 | WKWebView + 공유 쿠키 전략 추가. LinkedIn·Medium 전체 본문 추출 가능하도록 계획 수정. |
| 2026-04-14 | 백엔드 개발자 역할 섹션 추가. |
| 2026-04-14 | Step 1~7 구현 완료. project.yml SwiftSoup 패키지 추가. SavedItem 모델 업데이트. MetadataService / ArticleService / WebContentService / FetchCoordinator 구현. LibraryCardView·ItemDetailView UI 연결. 포그라운드 진입 시 자동 크롤링 트리거. |
| 2026-04-14 | 동작 확인: LinkedIn ✅, YouTube ✅ (OG+설명), Reddit ❌ (봇 감지). Library 자동 갱신 버그 수정 (scenePhase 구독 추가). CI SwiftSoup 패키지 resolve 단계 추가. |
| 2026-04-14 | "지금 읽기" 딥링크 개선: briefly://item?url= 스킴으로 Library 탭 전환 + 해당 아이템 상세 화면 자동 이동. NavigationStack(path:) 도입. ItemDetailView 본문 텍스트 펼치기/접기 추가. |
| 2026-04-14 | URL 스킴 YAML 들여쓰기 버그 수정 (CFBundleURLSchemes 하위 항목 들여쓰기 오류로 briefly:// 스킴 미등록). YouTube 본문 ogDescription 폴백 추가. |

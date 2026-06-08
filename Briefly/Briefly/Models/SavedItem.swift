import Foundation

// SavedItem.swift는 Briefly 타겟과 BrieflyShareExtension 타겟
// 양쪽 모두 Target Membership에 추가해야 합니다.
struct SavedItem: Codable, Identifiable, Hashable {
    let id: UUID
    let url: URL
    var title: String?
    let savedAt: Date
    var status: Status

    // 서버 content_id — POST /api/v1/swipe 호출 시 사용
    var serverContentId: Int?

    // Phase 2a — 크롤링 결과
    var ogTitle: String?
    var ogImageURL: URL?
    var ogDescription: String?
    var siteName: String?
    var articleText: String?
    var fetchStatus: FetchStatus

    // Phase 2b — AI 요약
    var summary: String?
    var summaryStatus: SummaryStatus

    enum SummaryStatus: String, Codable {
        case unknown    // 초기 상태 (기존 데이터 하위 호환용)
        case failed     // 타임아웃 초과 — 수동 재시도 필요
        case done       // 요약 완료
    }

    enum Status: String, Codable {
        case unread, read, discarded
        case kept       // Keep 선택 → Saved 탭
        case deleted    // Discard 선택 → Discarded 탭
    }

    enum FetchStatus: String, Codable {
        case pending    // 아직 시도 안 함
        case fetching   // 진행 중
        case done       // 완료
        case failed     // 실패 (OG도 못 가져옴)
        case partial    // OG만 성공, 본문 실패
    }

    init(url: URL, title: String? = nil) {
        self.id = UUID()
        self.url = url
        self.title = title
        self.savedAt = Date()
        self.status = .unread
        self.fetchStatus = .pending
        self.summaryStatus = .unknown
    }

    // summaryStatus 필드가 없는 기존 JSON과 하위 호환
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id            = try c.decode(UUID.self, forKey: .id)
        url           = try c.decode(URL.self, forKey: .url)
        title         = try? c.decode(String.self, forKey: .title)
        savedAt       = try c.decode(Date.self, forKey: .savedAt)
        status        = try c.decode(Status.self, forKey: .status)
        serverContentId = try? c.decode(Int.self, forKey: .serverContentId)
        ogTitle       = try? c.decode(String.self, forKey: .ogTitle)
        ogImageURL    = try? c.decode(URL.self, forKey: .ogImageURL)
        ogDescription = try? c.decode(String.self, forKey: .ogDescription)
        siteName      = try? c.decode(String.self, forKey: .siteName)
        articleText   = try? c.decode(String.self, forKey: .articleText)
        fetchStatus   = (try? c.decode(FetchStatus.self, forKey: .fetchStatus)) ?? .pending
        summary       = try? c.decode(String.self, forKey: .summary)
        summaryStatus = (try? c.decode(SummaryStatus.self, forKey: .summaryStatus)) ?? .unknown
    }

    /// 표시용 제목 — ogTitle → title → 도메인
    var displayTitle: String {
        let raw = ogTitle ?? title ?? url.host ?? url.absoluteString
        // LinkedIn 포스팅은 ogTitle에 포스팅 본문 전체가 들어있으므로 20자로 축약
        if siteName == "LinkedIn", raw.count > 20 {
            return String(raw.prefix(20)) + "..."
        }
        return raw
    }

    /// 도메인만 추출 (예: "medium.com")
    var domain: String {
        url.host ?? url.absoluteString
    }
}

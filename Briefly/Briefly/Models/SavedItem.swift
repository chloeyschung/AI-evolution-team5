import Foundation

// SavedItem.swift는 Briefly 타겟과 BrieflyShareExtension 타겟
// 양쪽 모두 Target Membership에 추가해야 합니다.
struct SavedItem: Codable, Identifiable {
    let id: UUID
    let url: URL
    var title: String?
    let savedAt: Date
    var status: Status

    // Phase 2a — 크롤링 결과
    var ogTitle: String?
    var ogImageURL: URL?
    var ogDescription: String?
    var siteName: String?
    var articleText: String?
    var fetchStatus: FetchStatus

    enum Status: String, Codable {
        case unread, read, discarded
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
    }

    /// 표시용 제목 — ogTitle → title → 도메인
    var displayTitle: String {
        ogTitle ?? title ?? url.host ?? url.absoluteString
    }

    /// 도메인만 추출 (예: "medium.com")
    var domain: String {
        url.host ?? url.absoluteString
    }
}

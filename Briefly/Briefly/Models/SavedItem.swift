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

    enum Status: String, Codable {
        case unread, read, discarded
        case kept       // Keep 선택 → Archived 탭
        case deleted    // Delete 선택 → Deleted 탭
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

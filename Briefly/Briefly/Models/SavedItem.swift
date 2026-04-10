import Foundation

// SavedItem.swift는 Briefly 타겟과 BrieflyShareExtension 타겟
// 양쪽 모두 Target Membership에 추가해야 합니다.
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

    /// 표시용 제목 — title이 없으면 도메인만
    var displayTitle: String {
        title ?? url.host ?? url.absoluteString
    }

    /// 도메인만 추출 (예: "medium.com")
    var domain: String {
        url.host ?? url.absoluteString
    }
}

import Foundation

// Target Membership: Briefly + BrieflyShareExtension 양쪽 모두 등록 필요
// (BrieflyAPI가 두 타겟 모두에 포함되므로 공유 타입도 양쪽 등록)
struct ServerContent: Codable, Identifiable {
    let id: Int
    let url: URL
    let title: String?
    let platform: String
    let thumbnailURL: URL?
    let summary: String?
    let createdAt: Date
    let autoTagCategory: String?
    let autoTagKeywordsEn: [String]
    let autoTagKeywordsOriginal: [String]

    var normalizedDomain: String { url.normalizedDomain }

    enum CodingKeys: String, CodingKey {
        case id, url, title, platform, summary
        case thumbnailURL        = "thumbnail_url"
        case createdAt           = "created_at"
        case autoTagCategory     = "auto_tag_category"
        case autoTagKeywordsEn   = "auto_tag_keywords_en"
        case autoTagKeywordsOriginal = "auto_tag_keywords_original"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id       = try  c.decode(Int.self,    forKey: .id)
        let raw  = try  c.decode(String.self, forKey: .url)
        url      = URL(string: raw) ?? URL(string: "https://briefly.app")!
        title    = try? c.decode(String.self, forKey: .title)
        platform = (try? c.decode(String.self, forKey: .platform)) ?? ""
        summary  = try? c.decode(String.self, forKey: .summary)

        if let thumbStr = try? c.decode(String.self, forKey: .thumbnailURL) {
            thumbnailURL = URL(string: thumbStr)
        } else {
            thumbnailURL = nil
        }

        let dateStr = try c.decode(String.self, forKey: .createdAt)
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = iso.date(from: dateStr) {
            createdAt = d
        } else {
            iso.formatOptions = [.withInternetDateTime]
            createdAt = iso.date(from: dateStr) ?? Date()
        }

        autoTagCategory         = try? c.decode(String.self,    forKey: .autoTagCategory)
        autoTagKeywordsEn       = (try? c.decode([String].self, forKey: .autoTagKeywordsEn))       ?? []
        autoTagKeywordsOriginal = (try? c.decode([String].self, forKey: .autoTagKeywordsOriginal)) ?? []
    }
}

import Foundation

// Target Membership: Briefly + BrieflyShareExtension 양쪽 모두 등록 필요
struct TopicCluster: Codable, Identifiable {
    let id: Int
    let titleKo: String
    let keywordsEn: [String]
    let contentIds: [Int]
    let generatedAt: Date?

    enum CodingKeys: String, CodingKey {
        case id
        case titleKo     = "title_ko"
        case keywordsEn  = "keywords_en"
        case contentIds  = "content_ids"
        case generatedAt = "generated_at"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id         = try  c.decode(Int.self,    forKey: .id)
        titleKo    = try  c.decode(String.self, forKey: .titleKo)
        keywordsEn = (try? c.decode([String].self, forKey: .keywordsEn)) ?? []
        contentIds = (try? c.decode([Int].self,    forKey: .contentIds)) ?? []

        if let dateStr = try? c.decode(String.self, forKey: .generatedAt) {
            let iso = ISO8601DateFormatter()
            iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let d = iso.date(from: dateStr) {
                generatedAt = d
            } else {
                iso.formatOptions = [.withInternetDateTime]
                generatedAt = iso.date(from: dateStr)
            }
        } else {
            generatedAt = nil
        }
    }
}

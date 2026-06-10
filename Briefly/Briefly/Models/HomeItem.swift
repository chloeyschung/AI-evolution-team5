import Foundation

enum HomeItem: Identifiable {
    case local(SavedItem)
    case server(ServerContent)

    var id: String {
        switch self {
        case .local(let item):     return "L-\(item.id.uuidString)"
        case .server(let content): return "S-\(content.id)"
        }
    }

    var url: URL {
        switch self {
        case .local(let item):     return item.url
        case .server(let content): return content.url
        }
    }

    var displayTitle: String {
        switch self {
        case .local(let item):     return item.displayTitle
        case .server(let content): return content.title ?? content.url.host ?? content.url.absoluteString
        }
    }

    var thumbnailURL: URL? {
        switch self {
        case .local(let item):     return item.ogImageURL
        case .server(let content): return content.thumbnailURL
        }
    }

    var normalizedDomain: String {
        switch self {
        case .local(let item):     return item.url.normalizedDomain
        case .server(let content): return content.normalizedDomain
        }
    }

    var savedAt: Date {
        switch self {
        case .local(let item):     return item.savedAt
        case .server(let content): return content.createdAt
        }
    }

    // IOS-007 sync 후 채워짐; 폴백 모드(고정 카테고리 그룹핑)에서 사용
    var autoTagCategory: String? {
        switch self {
        case .local(let item):     return item.autoTagCategory
        case .server(let content): return content.autoTagCategory
        }
    }

    var autoTagKeywords: [String] {
        switch self {
        case .local(let item):     return item.autoTagKeywordsEn
        case .server(let content): return content.autoTagKeywordsEn
        }
    }

    var serverContentId: Int? {
        switch self {
        case .local(let item):     return item.serverContentId
        case .server(let content): return content.id
        }
    }
}

// MARK: - URL helper

extension URL {
    var normalizedDomain: String {
        guard let host else { return absoluteString }
        return host.hasPrefix("www.") ? String(host.dropFirst(4)) : host
    }
}

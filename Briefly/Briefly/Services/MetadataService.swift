import Foundation
import SwiftSoup

struct PageMetadata {
    var ogTitle: String?
    var ogImageURL: URL?
    var ogDescription: String?
    var siteName: String?
}

actor MetadataService {

    static let shared = MetadataService()

    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 10
        return URLSession(configuration: config)
    }()

    func fetchMetadata(for url: URL) async throws -> PageMetadata {
        var request = URLRequest(url: url)
        request.setValue(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            forHTTPHeaderField: "User-Agent"
        )

        let (data, _) = try await session.data(for: request)
        guard let html = String(data: data, encoding: .utf8) ?? String(data: data, encoding: .isoLatin1) else {
            throw URLError(.cannotDecodeContentData)
        }

        return try parseMetadata(from: html, baseURL: url)
    }

    private func parseMetadata(from html: String, baseURL: URL) throws -> PageMetadata {
        let doc = try SwiftSoup.parse(html)
        var meta = PageMetadata()

        // og:title → <title>
        meta.ogTitle = ogContent(doc, property: "og:title")
            ?? (try? doc.title()).flatMap { $0.isEmpty ? nil : $0 }

        // og:image
        if let raw = ogContent(doc, property: "og:image"), !raw.isEmpty {
            meta.ogImageURL = URL(string: raw) ?? URL(string: raw, relativeTo: baseURL)
        }

        // og:description → <meta name="description">
        meta.ogDescription = ogContent(doc, property: "og:description")
            ?? metaName(doc, name: "description")

        // og:site_name → 도메인 폴백
        meta.siteName = ogContent(doc, property: "og:site_name")
            ?? baseURL.host

        return meta
    }

    private func ogContent(_ doc: Document, property: String) -> String? {
        guard
            let el = try? doc.select("meta[property=\(property)]").first(),
            let val = try? el.attr("content"),
            !val.isEmpty
        else { return nil }
        return val
    }

    private func metaName(_ doc: Document, name: String) -> String? {
        guard
            let el = try? doc.select("meta[name=\(name)]").first(),
            let val = try? el.attr("content"),
            !val.isEmpty
        else { return nil }
        return val
    }
}

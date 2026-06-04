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

    /// LinkedIn oEmbed API로 메타데이터를 빠르게 취득합니다 (인증 불필요, 공개 게시물 한정).
    func fetchLinkedInMetadata(for url: URL) async throws -> PageMetadata {
        let encoded = url.absoluteString.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        guard let oembedURL = URL(string: "https://www.linkedin.com/oembed?url=\(encoded)&format=json") else {
            throw URLError(.badURL)
        }
        let (data, _) = try await session.data(from: oembedURL)
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw URLError(.cannotParseResponse)
        }
        var meta = PageMetadata()
        meta.ogTitle = json["title"] as? String
        meta.ogDescription = json["author_name"] as? String
        meta.siteName = "LinkedIn"
        if let thumbURL = json["thumbnail_url"] as? String {
            meta.ogImageURL = URL(string: thumbURL)
        }
        return meta
    }

    /// YouTube oEmbed API로 메타데이터를 빠르게 취득합니다 (전체 HTML 파싱 불필요).
    func fetchYouTubeMetadata(for url: URL) async throws -> PageMetadata {
        let encoded = url.absoluteString.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        guard let oembedURL = URL(string: "https://www.youtube.com/oembed?url=\(encoded)&format=json") else {
            throw URLError(.badURL)
        }
        let (data, _) = try await session.data(from: oembedURL)
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw URLError(.cannotParseResponse)
        }
        var meta = PageMetadata()
        meta.ogTitle = json["title"] as? String
        meta.ogDescription = json["author_name"] as? String
        meta.siteName = "YouTube"
        // oEmbed thumbnail → og:image 대신 사용
        if let thumbURL = json["thumbnail_url"] as? String {
            meta.ogImageURL = URL(string: thumbURL)
        }
        return meta
    }

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

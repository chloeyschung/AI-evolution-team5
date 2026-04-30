import Foundation
import SwiftSoup

actor ArticleService {

    static let shared = ArticleService()

    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 10
        return URLSession(configuration: config)
    }()

    /// 500자 미만이면 WKWebView 폴백이 필요하다는 신호
    static let minimumArticleLength = 500

    func fetchArticleText(for url: URL) async throws -> String? {
        var request = URLRequest(url: url)
        request.setValue(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            forHTTPHeaderField: "User-Agent"
        )

        let (data, _) = try await session.data(for: request)
        guard let html = String(data: data, encoding: .utf8) ?? String(data: data, encoding: .isoLatin1) else {
            return nil
        }

        return try extractText(from: html)
    }

    private func extractText(from html: String) throws -> String? {
        let doc = try SwiftSoup.parse(html)

        // <article>, <main>, [role="main"] 순서로 탐색
        let candidates = ["article", "main", "[role=main]", ".post-content", ".entry-content"]
        for selector in candidates {
            if let container = try? doc.select(selector).first() {
                let text = paragraphText(from: container)
                if text.count >= ArticleService.minimumArticleLength {
                    return text
                }
            }
        }

        // 폴백: <body> 전체 <p> 태그
        if let body = try? doc.body() {
            let text = paragraphText(from: body)
            return text.isEmpty ? nil : text
        }

        return nil
    }

    private func paragraphText(from element: Element) -> String {
        let paragraphs = (try? element.select("p")) ?? Elements()
        let lines = paragraphs.compactMap { p -> String? in
            let text = (try? p.text()) ?? ""
            return text.isEmpty ? nil : text
        }
        return lines.joined(separator: "\n\n")
    }
}

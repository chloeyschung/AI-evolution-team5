import Foundation
import WebKit

/// JS 렌더링이 필요한 사이트 (LinkedIn, Medium 유료, Instagram 등)를
/// WKWebView + 공유 쿠키 스토어로 크롤링합니다.
///
/// - Note: MainActor에서만 생성·호출해야 합니다 (WKWebView 제약).
@MainActor
final class WebContentService: NSObject {

    static let shared = WebContentService()

    private var webView: WKWebView?
    private var continuation: CheckedContinuation<String?, Error>?
    private var timeoutTask: Task<Void, Never>?

    private static let timeoutSeconds: TimeInterval = 10

    /// WKWebView 폴백을 적용할 도메인 목록
    static let webViewDomains: Set<String> = [
        "linkedin.com",
        "medium.com",
        "instagram.com"
    ]

    static func needsWebView(for url: URL) -> Bool {
        guard let host = url.host?.lowercased() else { return false }
        return webViewDomains.contains(where: { host == $0 || host.hasSuffix("." + $0) })
    }

    func fetchWithWebView(url: URL) async throws -> String? {
        // 공유 쿠키 스토어 사용 — Safari 로그인 세션 공유
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()

        let wv = WKWebView(frame: .zero, configuration: config)
        wv.navigationDelegate = self
        self.webView = wv

        return try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation

            // 타임아웃
            timeoutTask = Task { [weak self] in
                try? await Task.sleep(nanoseconds: UInt64(WebContentService.timeoutSeconds * 1_000_000_000))
                guard !Task.isCancelled else { return }
                self?.finish(with: nil)
            }

            wv.load(URLRequest(url: url))
        }
    }

    private func finish(with result: String?) {
        timeoutTask?.cancel()
        continuation?.resume(returning: result)
        continuation = nil
        webView?.navigationDelegate = nil
        webView = nil
    }

    private func finishWithError(_ error: Error) {
        timeoutTask?.cancel()
        continuation?.resume(throwing: error)
        continuation = nil
        webView?.navigationDelegate = nil
        webView = nil
    }
}

extension WebContentService: WKNavigationDelegate {

    nonisolated func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        Task { @MainActor [weak self] in
            let js = """
            (function() {
                var article = document.querySelector('article') ||
                              document.querySelector('main') ||
                              document.querySelector('[role="main"]');
                if (article) return article.innerText;
                return document.body ? document.body.innerText : '';
            })();
            """
            do {
                let result = try await webView.evaluateJavaScript(js)
                self?.finish(with: result as? String)
            } catch {
                self?.finish(with: nil)
            }
        }
    }

    nonisolated func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        Task { @MainActor [weak self] in
            self?.finish(with: nil)
        }
    }

    nonisolated func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        Task { @MainActor [weak self] in
            self?.finish(with: nil)
        }
    }
}

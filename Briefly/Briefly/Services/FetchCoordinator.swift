import Foundation

extension Notification.Name {
    static let fetchCoordinatorDidUpdate = Notification.Name("FetchCoordinatorDidUpdate")
}

/// pending 상태의 SavedItem을 최대 3개 동시에 크롤링하는 코디네이터
@MainActor
final class FetchCoordinator {

    static let shared = FetchCoordinator()

    private var inProgress = false

    func fetchIfNeeded(for items: [SavedItem]) async {
        guard !inProgress else { return }
        inProgress = true
        defer { inProgress = false }

        let pending = items.filter { $0.fetchStatus == .pending }
        guard !pending.isEmpty else { return }

        await withTaskGroup(of: Void.self) { group in
            var running = 0
            for item in pending {
                // 최대 3개 동시 실행
                if running >= 3 {
                    await group.next()
                    running -= 1
                }
                running += 1
                group.addTask { [weak self] in
                    await self?.fetchOne(item: item)
                }
            }
        }
    }

    private func fetchOne(item: SavedItem) async {
        var updated = item
        updated.fetchStatus = .fetching
        StorageService.shared.updateItem(updated)

        do {
            // 1단계: OG 메타데이터 (URLSession)
            let meta = try await MetadataService.shared.fetchMetadata(for: item.url)
            updated.ogTitle = meta.ogTitle
            updated.ogImageURL = meta.ogImageURL
            updated.ogDescription = meta.ogDescription
            updated.siteName = meta.siteName

            // 2단계: 본문 텍스트
            let articleText = try await fetchArticleText(for: item.url)
            updated.articleText = articleText
            updated.fetchStatus = (articleText != nil) ? .done : .partial

        } catch {
            // OG도 실패하면 failed, OG만 있으면 partial
            if updated.ogTitle != nil {
                updated.fetchStatus = .partial
            } else {
                updated.fetchStatus = .failed
            }
        }

        StorageService.shared.updateItem(updated)
        NotificationCenter.default.post(name: .fetchCoordinatorDidUpdate, object: nil)
    }

    /// ArticleService 시도 후 결과가 짧으면 WebContentService 폴백
    private func fetchArticleText(for url: URL) async throws -> String? {
        // WebView 전용 도메인은 바로 WebContentService
        if WebContentService.needsWebView(for: url) {
            return try await WebContentService.shared.fetchWithWebView(url: url)
        }

        // URLSession 먼저
        let text = try await ArticleService.shared.fetchArticleText(for: url)
        if let text, text.count >= ArticleService.minimumArticleLength {
            return text
        }

        // 결과가 짧으면 WKWebView 폴백
        return try await WebContentService.shared.fetchWithWebView(url: url)
    }
}

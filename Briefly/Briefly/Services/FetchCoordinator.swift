import Foundation

extension Notification.Name {
    static let fetchCoordinatorDidUpdate = Notification.Name("FetchCoordinatorDidUpdate")
    static let brieflyOpenItem = Notification.Name("BrieflyOpenItem")
}

/// pending 상태의 SavedItem을 최대 3개 동시에 크롤링하는 코디네이터
@MainActor
final class FetchCoordinator {

    static let shared = FetchCoordinator()

    private var inProgress = false

    func fetchIfNeeded(for items: [SavedItem]) async {
        guard !inProgress else {
            print("[Fetch] 이미 진행 중, 스킵")
            return
        }
        inProgress = true
        defer { inProgress = false }

        let pending = items.filter { $0.fetchStatus == .pending }
        print("[Fetch] 대기 중인 항목: \(pending.count)개 / 전체: \(items.count)개")
        guard !pending.isEmpty else { return }

        for item in pending {
            await fetchOne(item: item)
        }
    }

    private func fetchOne(item: SavedItem) async {
        print("[Fetch] 시작: \(item.url)")
        var updated = item
        updated.fetchStatus = .fetching
        StorageService.shared.updateItem(updated)
        NotificationCenter.default.post(name: .fetchCoordinatorDidUpdate, object: nil)

        do {
            // 1단계: OG 메타데이터 (URLSession)
            let meta = try await MetadataService.shared.fetchMetadata(for: item.url)
            updated.ogTitle = meta.ogTitle
            updated.ogImageURL = meta.ogImageURL
            updated.ogDescription = meta.ogDescription
            updated.siteName = meta.siteName
            print("[Fetch] OG 완료: title=\(meta.ogTitle ?? "nil"), image=\(meta.ogImageURL?.absoluteString ?? "nil")")

            // 2단계: 본문 텍스트
            let articleText = try await fetchArticleText(for: item.url)
            // 본문이 없으면 ogDescription을 폴백으로 사용 (YouTube, 영상 플랫폼 등)
            updated.articleText = articleText ?? updated.ogDescription
            updated.fetchStatus = (articleText != nil) ? .done : .partial
            print("[Fetch] 본문 완료: \(updated.articleText?.count ?? 0)자, status=\(updated.fetchStatus)")

        } catch {
            print("[Fetch] 에러: \(error)")
            // 에러가 나도 ogDescription이 있으면 폴백으로 저장
            updated.articleText = updated.ogDescription
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

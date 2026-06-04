import Foundation

extension Notification.Name {
    static let fetchCoordinatorDidUpdate = Notification.Name("FetchCoordinatorDidUpdate")
    static let brieflyOpenItem = Notification.Name("BrieflyOpenItem")
    static let authSessionDidExpire = Notification.Name("AuthSessionDidExpire")
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
            // 1단계: OG 메타데이터
            // YouTube는 oEmbed API로 빠르게 취득, 그 외는 HTML 파싱
            let meta: PageMetadata
            if Self.isYouTubeURL(item.url),
               let ytMeta = try? await MetadataService.shared.fetchYouTubeMetadata(for: item.url) {
                meta = ytMeta
            } else {
                meta = try await MetadataService.shared.fetchMetadata(for: item.url)
            }
            updated.ogTitle = meta.ogTitle
            updated.ogImageURL = meta.ogImageURL
            updated.ogDescription = meta.ogDescription
            updated.siteName = meta.siteName
            print("[Fetch] OG 완료: title=\(meta.ogTitle ?? "nil"), image=\(meta.ogImageURL?.absoluteString ?? "nil")")

            // OG 완료 즉시 저장 + 알림 — 이미지가 바로 표시되도록
            StorageService.shared.updateItem(updated)
            NotificationCenter.default.post(name: .fetchCoordinatorDidUpdate, object: nil)

            // 2단계: 본문 텍스트
            // YouTube는 스크래핑이 불가하므로 ogDescription을 즉시 사용
            if Self.isYouTubeURL(item.url) {
                updated.articleText = updated.ogDescription
                updated.fetchStatus = .partial
                print("[Fetch] YouTube — ogDescription 사용: \(updated.articleText?.count ?? 0)자")
            } else {
                let articleText = try await fetchArticleText(for: item.url)
                updated.articleText = articleText ?? updated.ogDescription
                updated.fetchStatus = (articleText != nil) ? .done : .partial
                print("[Fetch] 본문 완료: \(updated.articleText?.count ?? 0)자, status=\(updated.fetchStatus)")
            }

        } catch {
            print("[Fetch] 에러: \(error)")
            updated.articleText = updated.ogDescription
            updated.fetchStatus = updated.ogTitle != nil ? .partial : .failed
        }

        StorageService.shared.updateItem(updated)
        NotificationCenter.default.post(name: .fetchCoordinatorDidUpdate, object: nil)
    }

    private static func isYouTubeURL(_ url: URL) -> Bool {
        guard let host = url.host?.lowercased() else { return false }
        return host == "youtube.com" || host.hasSuffix(".youtube.com") || host == "youtu.be"
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

import Foundation

/// App Group UserDefaults를 통해 메인 앱과 Share Extension 간 데이터를 공유합니다.
///
/// inbox/drain 패턴:
/// - Extension은 "inbox" 키에만 씁니다 (동시 쓰기 race condition 방지)
/// - 메인 앱이 포그라운드로 올 때 inbox를 drain하여 main에 merge합니다
final class StorageService {
    static let shared = StorageService()

    private let appGroupID = "group.com.briefly.shared"
    private let mainKey = "savedItems"
    private let inboxKey = "brieflyInbox"

    private var defaults: UserDefaults? {
        UserDefaults(suiteName: appGroupID)
    }

    private init() {}

    // MARK: - Extension 전용: inbox에 추가

    /// Share Extension에서 호출. inbox에 항목을 추가합니다.
    func appendToInbox(_ item: SavedItem) {
        guard let defaults else {
            print("[StorageService] App Group 접근 실패. entitlements 설정을 확인하세요.")
            return
        }
        var inbox = decode(from: defaults, key: inboxKey)
        inbox.append(item)
        encode(inbox, to: defaults, key: inboxKey)
        // Extension이 닫히기 전에 디스크에 flush
        defaults.synchronize()
    }

    // MARK: - 메인 앱 전용: drain 후 merge

    /// 메인 앱에서 호출. inbox를 main으로 merge하고 최종 목록을 반환합니다.
    @discardableResult
    func drainInboxAndLoad() -> [SavedItem] {
        guard let defaults else {
            print("[StorageService] App Group 접근 실패. entitlements 설정을 확인하세요.")
            return []
        }

        let inbox = decode(from: defaults, key: inboxKey)
        var main = decode(from: defaults, key: mainKey)

        if !inbox.isEmpty {
            // 중복 URL 제거: 이미 있는 URL이면 savedAt만 갱신
            let existingURLs = Set(main.map(\.url))
            let newItems = inbox.filter { !existingURLs.contains($0.url) }
            main.append(contentsOf: newItems)
            main.sort { $0.savedAt > $1.savedAt }
            encode(main, to: defaults, key: mainKey)
            defaults.removeObject(forKey: inboxKey)
        }

        return main
    }

    /// 메인 앱에서 항목 상태 업데이트 (read, discarded 등)
    func updateItem(_ item: SavedItem) {
        guard let defaults else { return }
        var items = decode(from: defaults, key: mainKey)
        if let idx = items.firstIndex(where: { $0.id == item.id }) {
            items[idx] = item
            encode(items, to: defaults, key: mainKey)
        }
    }

    /// inbox + main 전체 항목을 반환합니다. (로그인 후 동기화용)
    func loadAll() -> [SavedItem] {
        guard let defaults else { return [] }
        let main = decode(from: defaults, key: mainKey)
        let inbox = decode(from: defaults, key: inboxKey)
        return main + inbox
    }

    /// inbox 또는 main 어디에 있든 항목을 업데이트합니다.
    /// Share Extension에서 serverContentId를 나중에 기록할 때 사용합니다.
    func updateItemById(_ item: SavedItem) {
        guard let defaults else { return }

        var inbox = decode(from: defaults, key: inboxKey)
        if let idx = inbox.firstIndex(where: { $0.id == item.id }) {
            inbox[idx] = item
            encode(inbox, to: defaults, key: inboxKey)
            return
        }

        var main = decode(from: defaults, key: mainKey)
        if let idx = main.firstIndex(where: { $0.id == item.id }) {
            main[idx] = item
            encode(main, to: defaults, key: mainKey)
        }
    }

    /// 특정 항목의 AI 요약을 업데이트합니다.
    func updateSummary(for id: UUID, summary: String) {
        guard let defaults else { return }
        var items = decode(from: defaults, key: mainKey)
        if let idx = items.firstIndex(where: { $0.id == id }) {
            items[idx].summary = summary
            encode(items, to: defaults, key: mainKey)
        }
    }

    /// 특정 항목의 AI 요약 상태를 업데이트합니다 (inbox/main 모두 확인).
    func updateSummaryStatus(for id: UUID, status: SavedItem.SummaryStatus) {
        guard let defaults else { return }

        var inbox = decode(from: defaults, key: inboxKey)
        if let idx = inbox.firstIndex(where: { $0.id == id }) {
            inbox[idx].summaryStatus = status
            encode(inbox, to: defaults, key: inboxKey)
            return
        }

        var items = decode(from: defaults, key: mainKey)
        if let idx = items.firstIndex(where: { $0.id == id }) {
            items[idx].summaryStatus = status
            encode(items, to: defaults, key: mainKey)
        }
    }

    /// 특정 항목의 AI 자동 태그를 업데이트합니다 (inbox/main 모두 확인).
    func updateAutoTags(for id: UUID, category: String?, keywordsEn: [String], keywordsOriginal: [String]) {
        guard let defaults else { return }

        var inbox = decode(from: defaults, key: inboxKey)
        if let idx = inbox.firstIndex(where: { $0.id == id }) {
            inbox[idx].autoTagCategory = category
            inbox[idx].autoTagKeywordsEn = keywordsEn
            inbox[idx].autoTagKeywordsOriginal = keywordsOriginal
            encode(inbox, to: defaults, key: inboxKey)
            return
        }

        var items = decode(from: defaults, key: mainKey)
        if let idx = items.firstIndex(where: { $0.id == id }) {
            items[idx].autoTagCategory = category
            items[idx].autoTagKeywordsEn = keywordsEn
            items[idx].autoTagKeywordsOriginal = keywordsOriginal
            encode(items, to: defaults, key: mainKey)
        }
    }

    // MARK: - IOS-007: 서버 summary · auto-tag 병합

    /// 서버 fetch 결과를 로컬 SavedItem에 병합합니다.
    /// serverContentId 매칭 → auto-tag(서버 값 있을 때만) · summary(로컬 미완료 시) 업데이트.
    func mergeServerData(_ serverItems: [ServerContent]) {
        guard let defaults else { return }
        var items = decode(from: defaults, key: mainKey)
        var updated = false
        for server in serverItems {
            guard let idx = items.firstIndex(where: { $0.serverContentId == server.id }) else { continue }
            // auto-tag: 서버에 category 값이 있을 때만 덮어씀 (FR-6)
            if let category = server.autoTagCategory {
                items[idx].autoTagCategory = category
                items[idx].autoTagKeywordsEn = server.autoTagKeywordsEn
                items[idx].autoTagKeywordsOriginal = server.autoTagKeywordsOriginal
            }
            // summary: 로컬에 아직 없는 경우만 서버 값으로 업데이트 (FR-7)
            if items[idx].summaryStatus != .done, let summary = server.summary {
                items[idx].summary = summary
                items[idx].summaryStatus = .done
            }
            updated = true
        }
        if updated {
            encode(items, to: defaults, key: mainKey)
        }
    }

    // MARK: - Private helpers

    private func decode(from defaults: UserDefaults, key: String) -> [SavedItem] {
        guard let data = defaults.data(forKey: key) else { return [] }
        return (try? JSONDecoder().decode([SavedItem].self, from: data)) ?? []
    }

    private func encode(_ items: [SavedItem], to defaults: UserDefaults, key: String) {
        guard let data = try? JSONEncoder().encode(items) else { return }
        defaults.set(data, forKey: key)
    }
}

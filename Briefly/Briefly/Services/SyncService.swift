import Foundation

/// 로그인 직후 로컬에만 있는 항목(serverContentId == nil)을 서버에 일괄 업로드합니다.
final class SyncService {
    static let shared = SyncService()
    private init() {}

    func syncLocalItemsToServer(token: String) async {
        let items = StorageService.shared.loadAll()
        let unsynced = items.filter { $0.serverContentId == nil }
        guard !unsynced.isEmpty else { return }

        print("[SyncService] 업로드 시작 — \(unsynced.count)개 항목")

        await withTaskGroup(of: Void.self) { group in
            for item in unsynced {
                group.addTask {
                    guard let result = try? await BrieflyAPI.shared.share(url: item.url, token: token) else { return }
                    var updated = item
                    updated.serverContentId = result.id
                    StorageService.shared.updateItemById(updated)

                    if item.status == .kept {
                        try? await BrieflyAPI.shared.swipe(contentId: result.id, action: .keep, token: token)
                    } else if item.status == .deleted {
                        try? await BrieflyAPI.shared.swipe(contentId: result.id, action: .discard, token: token)
                    }
                }
            }
        }

        print("[SyncService] 업로드 완료")
        NotificationCenter.default.post(name: .fetchCoordinatorDidUpdate, object: nil)
    }
}

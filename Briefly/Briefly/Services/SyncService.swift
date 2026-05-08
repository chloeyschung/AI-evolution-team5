import Foundation

/// 로컬에만 있는 항목(serverContentId == nil)을 서버에 일괄 업로드합니다.
/// actor로 선언해 동시 호출을 직렬화합니다 (토큰 갱신 race condition 방지).
actor SyncService {
    static let shared = SyncService()
    private var isRunning = false

    func syncLocalItemsToServer() async {
        // 이미 실행 중이면 스킵 — actor가 await 지점에서 suspend될 때 두 번째 진입을 막음
        guard !isRunning else {
            print("[SyncService] 이미 실행 중 — 스킵")
            return
        }
        isRunning = true
        defer { isRunning = false }

        guard let storedToken = AuthTokenStore.shared.accessToken else {
            print("[SyncService] 토큰 없음 — 비로그인 상태")
            return
        }

        let items = StorageService.shared.loadAll()
        let unsynced = items.filter { $0.serverContentId == nil }
        print("[SyncService] 전체 \(items.count)개, 미동기화 \(unsynced.count)개")
        guard !unsynced.isEmpty else { return }

        var activeToken = storedToken
        var didRefreshToken = false

        for item in unsynced {
            print("[SyncService] share 시도: \(item.url)")
            do {
                let (result, newToken, wasRefreshed) = try await shareWithRefresh(
                    url: item.url, activeToken: activeToken, didRefreshToken: didRefreshToken
                )
                activeToken = newToken
                didRefreshToken = wasRefreshed

                print("[SyncService] share 성공: contentId=\(result.id)")
                var updated = item
                updated.serverContentId = result.id
                StorageService.shared.updateItemById(updated)

                if item.status == .kept {
                    do {
                        try await BrieflyAPI.shared.swipe(contentId: result.id, action: .keep, token: activeToken)
                        print("[SyncService] swipe keep 성공: contentId=\(result.id)")
                    } catch {
                        print("[SyncService] swipe keep 실패: \(error.localizedDescription)")
                    }
                } else if item.status == .deleted {
                    do {
                        try await BrieflyAPI.shared.swipe(contentId: result.id, action: .discard, token: activeToken)
                        print("[SyncService] swipe discard 성공: contentId=\(result.id)")
                    } catch {
                        print("[SyncService] swipe discard 실패: \(error.localizedDescription)")
                    }
                }
            } catch {
                print("[SyncService] share 실패: \(item.url) — \(error.localizedDescription)")
            }
        }

        print("[SyncService] 업로드 완료")
        await MainActor.run {
            NotificationCenter.default.post(name: .fetchCoordinatorDidUpdate, object: nil)
        }
    }

    // MARK: - Private

    /// 401 수신 시 토큰을 갱신하고 한 번 재시도합니다.
    private func shareWithRefresh(
        url: URL,
        activeToken: String,
        didRefreshToken: Bool
    ) async throws -> (BrieflyAPI.ShareResult, String, Bool) {
        do {
            let result = try await BrieflyAPI.shared.share(url: url, token: activeToken)
            return (result, activeToken, didRefreshToken)
        } catch let error as BrieflyAPI.APIError {
            if case .httpError(401, _) = error, !didRefreshToken,
               let newToken = await BrieflyAPI.shared.refreshCurrentToken() {
                print("[SyncService] 401 → 토큰 갱신 후 재시도")
                let result = try await BrieflyAPI.shared.share(url: url, token: newToken)
                return (result, newToken, true)
            }
            throw error
        }
    }
}

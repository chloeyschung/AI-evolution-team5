import Foundation

final class RecentlyViewedStore {
    static let shared = RecentlyViewedStore()
    private let key = "briefly_recently_viewed_ids"
    private let maxCount = 20

    func record(_ id: UUID) {
        guard StorageService.shared.loadAll().contains(where: { $0.id == id }) else { return }
        var ids = loadIDs()
        ids.removeAll { $0 == id.uuidString }
        ids.insert(id.uuidString, at: 0)
        UserDefaults.standard.set(Array(ids.prefix(maxCount)), forKey: key)
    }

    func recentItems(from all: [SavedItem]) -> [SavedItem] {
        let ids = loadIDs()
        let map = Dictionary(uniqueKeysWithValues: all.map { ($0.id.uuidString, $0) })
        return ids.compactMap { map[$0] }
    }

    private func loadIDs() -> [String] {
        UserDefaults.standard.stringArray(forKey: key) ?? []
    }
}

import Foundation
import SwiftUI

// MARK: - HomeCardSection

struct HomeCardSection: Identifiable {
    enum Kind {
        case date(HomeDateBucket)
        case source(String)           // 출처별 (normalized domain)
        case topic(TopicCluster)      // 주제별: 동적 클러스터 (IOS-008, 기본)
        case topicCategory(String)    // 주제별: 고정 카테고리 폴백 (auto_tag_category)
        case topicPlaceholder         // 주제별: Phase 1 로딩 플레이스홀더
    }

    let id: String
    let title: String
    let subtitle: String?             // 키워드 chips (선택 — 주제별 섹션에서 사용)
    let icon: String
    let items: [HomeItem]
    let kind: Kind
}

// MARK: - DailySeededRNG (xorshift64, 날짜 시드 — 하루 1회 섹션 순서 변경)

private struct DailySeededRNG: RandomNumberGenerator {
    var state: UInt64

    init(date: Date = Date()) {
        let c = Calendar.current.dateComponents([.year, .month, .day], from: date)
        let y = c.year ?? 2026
        let m = c.month ?? 1
        let d = c.day ?? 1
        let raw = UInt64(y * 10000 + m * 100 + d)
        state = raw == 0 ? 1 : raw
    }

    mutating func next() -> UInt64 {
        state ^= state << 13
        state ^= state >> 7
        state ^= state << 17
        return state
    }
}

// MARK: - HomeViewModel

@MainActor
final class HomeViewModel: ObservableObject {
    @Published var sections: [HomeCardSection] = []
    @Published var isLoadingServer = false
    @Published var isRefreshing = false

    /// ContentView의 FetchCoordinator 호출에 사용
    private(set) var localItems: [SavedItem] = []
    private var allItems: [HomeItem] = []

    func load() {
        loadLocal()
        Task { await loadServer() }
    }

    func reload() { load() }

    /// 데모용 수동 새로고침 — 서버 재클러스터링 후 새 클러스터 표시
    func demoRefresh() {
        guard !isRefreshing else { return }
        isRefreshing = true

        // refresh 실패 시 폴백용으로 현재 표시 중인 클러스터 보존
        let existingClusters: [TopicCluster] = sections.compactMap {
            if case .topic(let c) = $0.kind { return c } else { return nil }
        }

        Task {
            defer { isRefreshing = false }
            guard let token = AuthTokenStore.shared.accessToken else {
                print("[HomeViewModel] demoRefresh: 토큰 없음 — 로그인 필요")
                rebuildSections(clusters: existingClusters.isEmpty ? nil : existingClusters)
                return
            }
            print("[HomeViewModel] demoRefresh: 클러스터링 요청 중...")
            async let serverTask  = BrieflyAPI.shared.fetchServerContent(token: token)
            async let clusterTask = BrieflyAPI.shared.refreshTopicClusters(token: token)
            let serverItems   = (try? await serverTask)  ?? []
            let freshClusters = (try? await clusterTask) ?? []
            print("[HomeViewModel] demoRefresh: 새 클러스터 \(freshClusters.count)개 수신")

            // 새 클러스터가 있으면 사용, 없으면 기존 클러스터 유지
            let clusters = freshClusters.isEmpty ? existingClusters : freshClusters

            if !serverItems.isEmpty {
                StorageService.shared.mergeServerData(serverItems)
                localItems = StorageService.shared.loadAll().filter { $0.status != .deleted }
            }
            let localServerIds = Set(localItems.compactMap(\.serverContentId))
            let newServerItems = serverItems
                .filter { !localServerIds.contains($0.id) }
                .map { HomeItem.server($0) }
            allItems = localItems.map { .local($0) } + newServerItems
            withAnimation(.easeInOut(duration: 0.4)) {
                rebuildSections(clusters: clusters.isEmpty ? nil : clusters)
            }
        }
    }

    // MARK: Phase 1 — Local

    private func loadLocal() {
        localItems = StorageService.shared.drainInboxAndLoad()
            .filter { $0.status != .deleted }
        allItems = localItems.map { .local($0) }
        rebuildSections(clusters: nil)
    }

    // MARK: Phase 2 — Server

    private func loadServer() async {
        guard let token = AuthTokenStore.shared.accessToken else { return }
        isLoadingServer = true
        defer { isLoadingServer = false }

        async let serverTask  = BrieflyAPI.shared.fetchServerContent(token: token)
        async let clusterTask = BrieflyAPI.shared.fetchTopicClusters(token: token)

        let serverItems = (try? await serverTask)  ?? []
        let clusters    = (try? await clusterTask) ?? []

        // IOS-007: summary · auto-tag를 로컬 SavedItem에 병합 후 재로드
        if !serverItems.isEmpty {
            StorageService.shared.mergeServerData(serverItems)
            localItems = StorageService.shared.loadAll().filter { $0.status != .deleted }
        }

        // 로컬에 있는 serverContentId와 중복되는 서버 항목 제거
        let localServerIds = Set(localItems.compactMap(\.serverContentId))
        let newServerItems = serverItems
            .filter { !localServerIds.contains($0.id) }
            .map { HomeItem.server($0) }

        allItems = localItems.map { .local($0) } + newServerItems
        rebuildSections(clusters: clusters.isEmpty ? nil : clusters)
    }

    // MARK: Section building

    private func rebuildSections(clusters: [TopicCluster]?) {
        let allTopic = topicSections(clusters: clusters)

        let topicFixed = allTopic.filter {
            if case .topicPlaceholder = $0.kind { return false }
            return true
        }
        let topicPlaceholders = allTopic.filter {
            if case .topicPlaceholder = $0.kind { return true }
            return false
        }

        var utility = dateSections() + sourceSections() + topicPlaceholders
        var rng = DailySeededRNG()
        utility.shuffle(using: &rng)
        sections = topicFixed + utility
    }

    private func dateSections() -> [HomeCardSection] {
        var buckets: [HomeDateBucket: [HomeItem]] = [:]
        for item in allItems {
            let b = HomeDateBucket.bucket(for: item.savedAt)
            buckets[b, default: []].append(item)
        }
        return HomeDateBucket.allCases.compactMap { bucket in
            guard let items = buckets[bucket], !items.isEmpty else { return nil }
            return HomeCardSection(
                id: "date-\(bucket.rawValue)",
                title: bucket.rawValue,
                subtitle: nil,
                icon: "📅",
                items: items,
                kind: .date(bucket)
            )
        }
    }

    private func sourceSections() -> [HomeCardSection] {
        var groups: [String: [HomeItem]] = [:]
        for item in allItems {
            groups[item.normalizedDomain, default: []].append(item)
        }
        return groups
            .sorted { $0.value.count > $1.value.count }
            .prefix(8)
            .map { domain, items in
                HomeCardSection(
                    id: "src-\(domain)",
                    title: Self.brandName(for: domain),
                    subtitle: nil,
                    icon: "🌐",
                    items: items,
                    kind: .source(domain)
                )
            }
    }

    private func topicSections(clusters: [TopicCluster]?) -> [HomeCardSection] {
        // 동적 클러스터 모드 (IOS-008 결과)
        if let clusters {
            let idMap = Dictionary(
                allItems.compactMap { item -> (Int, HomeItem)? in
                    guard let sid = item.serverContentId else { return nil }
                    return (sid, item)
                },
                uniquingKeysWith: { first, _ in first }
            )
            let clusterSections = clusters.compactMap { cluster -> HomeCardSection? in
                let items = cluster.contentIds.compactMap { idMap[$0] }
                guard !items.isEmpty else { return nil }
                return HomeCardSection(
                    id: "topic-\(cluster.id)",
                    title: cluster.titleKo,
                    subtitle: cluster.keywordsEn.prefix(3).joined(separator: " · "),
                    icon: "📚",
                    items: items,
                    kind: .topic(cluster)
                )
            }
            if !clusterSections.isEmpty { return clusterSections }
        }

        // 폴백: auto_tag_category 그룹핑
        let tagged = allItems.filter { $0.autoTagCategory != nil }
        guard !tagged.isEmpty else {
            return [HomeCardSection(
                id: "topic-placeholder",
                title: "주제 분석 중",
                subtitle: nil,
                icon: "📚",
                items: [],
                kind: .topicPlaceholder
            )]
        }

        var catGroups: [String: [HomeItem]] = [:]
        for item in tagged {
            if let cat = item.autoTagCategory {
                catGroups[cat, default: []].append(item)
            }
        }
        return catGroups.map { cat, items in
            HomeCardSection(
                id: "topic-cat-\(cat)",
                title: Self.categoryLabel(cat),
                subtitle: Self.topKeywords(from: items).joined(separator: " · "),
                icon: "📚",
                items: items,
                kind: .topicCategory(cat)
            )
        }
    }

    // MARK: Helpers

    private static func brandName(for domain: String) -> String {
        switch domain {
        case "youtube.com":           return "YouTube"
        case "linkedin.com":          return "LinkedIn"
        case "medium.com":            return "Medium"
        case "twitter.com", "x.com": return "X"
        case "reddit.com":            return "Reddit"
        case "github.com":            return "GitHub"
        case "naver.com":             return "Naver"
        default:                      return domain
        }
    }

    private static func categoryLabel(_ category: String) -> String {
        switch category {
        case "Tech":      return "기술"
        case "Business":  return "비즈니스"
        case "Essays":    return "에세이"
        case "Research":  return "연구"
        case "Lifestyle": return "라이프스타일"
        case "News":      return "뉴스"
        case "Culture":   return "문화"
        case "Other":     return "기타"
        default:          return category
        }
    }

    private static func topKeywords(from items: [HomeItem]) -> [String] {
        var freq: [String: Int] = [:]
        for item in items {
            for kw in item.autoTagKeywords { freq[kw, default: 0] += 1 }
        }
        return freq.sorted { $0.value > $1.value }.prefix(3).map(\.key)
    }
}

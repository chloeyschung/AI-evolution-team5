import SwiftUI

struct SearchView: View {
    @State private var query = ""
    @State private var selectedCategories: Set<String> = []
    @State private var selectedDomains: Set<String>    = []
    @State private var activeDropdown: FilterDropdown? = nil
    @State private var recentItemsCache: [SavedItem]   = []

    init() {
        let all = StorageService.shared.loadAll().filter { $0.status != .deleted }
        _recentItemsCache = State(initialValue: RecentlyViewedStore.shared.recentItems(from: all))
    }

    private var trimmed: String { query.trimmingCharacters(in: .whitespaces) }
    private var hasActiveSearch: Bool {
        !trimmed.isEmpty || !selectedCategories.isEmpty || !selectedDomains.isEmpty
    }

    // MARK: - Data

    private var allItems: [SavedItem] {
        StorageService.shared.loadAll().filter { $0.status != .deleted }
    }

    private var availableCategories: [String] {
        Array(Set(allItems.compactMap(\.autoTagCategory))).sorted()
    }

    private var availableDomains: [String] {
        Array(Set(allItems.map { $0.url.normalizedDomain })).sorted()
    }

    private func refreshRecentItems() {
        recentItemsCache = RecentlyViewedStore.shared.recentItems(from: allItems)
    }

    private var results: [SavedItem] {
        guard hasActiveSearch else { return [] }
        var items = allItems

        if !trimmed.isEmpty {
            let q = trimmed.lowercased()
            items = items.filter { item in
                item.displayTitle.lowercased().contains(q) ||
                (item.ogDescription?.lowercased().contains(q) ?? false) ||
                (item.summary?.lowercased().contains(q) ?? false) ||
                (item.articleText?.lowercased().contains(q) ?? false) ||
                item.autoTagKeywordsEn.contains { $0.lowercased().contains(q) } ||
                item.autoTagKeywordsOriginal.contains { $0.lowercased().contains(q) } ||
                (item.autoTagCategory?.lowercased().contains(q) ?? false) ||
                (item.url.host?.lowercased().contains(q) ?? false)
            }
        }

        if !selectedCategories.isEmpty {
            items = items.filter { item in
                item.autoTagCategory.map { selectedCategories.contains($0) } ?? false
            }
        }

        if !selectedDomains.isEmpty {
            items = items.filter { selectedDomains.contains($0.url.normalizedDomain) }
        }

        return items.sorted { $0.savedAt > $1.savedAt }
    }

    // MARK: - Body

    var body: some View {
        VStack(spacing: 0) {
            CategoryPlatformFilterBar(
                availableCategories: availableCategories,
                availableDomains: availableDomains,
                selectedCategories: $selectedCategories,
                selectedDomains: $selectedDomains,
                activeDropdown: $activeDropdown,
                topPadding: 8
            ) {
                Group {
                    if !hasActiveSearch {
                        if recentItemsCache.isEmpty { emptyPrompt } else { recentlyViewedSection }
                    } else if results.isEmpty {
                        noResults
                    } else {
                        resultList
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .background(Color.brieflyBgApp.ignoresSafeArea())
        .onAppear { refreshRecentItems() }
        .navigationTitle("Search")
        .navigationBarTitleDisplayMode(.large)
        .searchable(text: $query, prompt: "제목, 키워드, 본문 검색...")
        .navigationDestination(for: SavedItem.self) { item in
            ItemDetailView(items: [item], startIndex: 0, showActions: true)
        }
    }

    // MARK: - Recently Viewed

    private var recentlyViewedSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("최근에 본 항목")
                .font(.brieflyH3)
                .foregroundStyle(Color.brieflyTextPrimary)
                .padding(.horizontal, 16)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(recentItemsCache) { item in
                        NavigationLink(value: item) {
                            RecentlyViewedCard(item: item)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 16)
            }
        }
        .padding(.top, 8)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    // MARK: - States

    private var emptyPrompt: some View {
        VStack(spacing: BrieflySpacing.s4) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 48))
                .foregroundStyle(Color.brieflyInk300)
            Text("저장한 콘텐츠를 검색해보세요")
                .font(.brieflyH2)
                .foregroundStyle(Color.brieflyTextPrimary)
            Text("제목, AI 키워드, 요약, 본문을 모두 검색합니다")
                .font(.brieflyBody)
                .foregroundStyle(Color.brieflyTextSecondary)
                .multilineTextAlignment(.center)
        }
        .padding()
    }

    private var noResults: some View {
        VStack(spacing: BrieflySpacing.s3) {
            Image(systemName: "doc.text.magnifyingglass")
                .font(.system(size: 40))
                .foregroundStyle(Color.brieflyInk300)
            Text(trimmed.isEmpty ? "조건에 맞는 항목이 없습니다" : "'\(trimmed)'에 대한 결과가 없습니다")
                .font(.brieflyH2)
                .foregroundStyle(Color.brieflyTextPrimary)
                .multilineTextAlignment(.center)
            Text("다른 키워드나 필터로 검색해보세요")
                .font(.brieflyBody)
                .foregroundStyle(Color.brieflyTextSecondary)
        }
        .padding()
    }

    private var resultList: some View {
        List {
            ForEach(results) { item in
                NavigationLink(value: item) {
                    LibraryCardView(item: item)
                        .padding(.vertical, 4)
                }
                .listRowBackground(Color.brieflyBgSurface)
                .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
                .listRowSeparator(.hidden)
            }
        }
        .listStyle(.plain)
        .background(Color.brieflyBgApp)
    }
}

// MARK: - RecentlyViewedCard

private struct RecentlyViewedCard: View {
    let item: SavedItem

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ZStack {
                Color.brieflyInk100
                if let url = item.ogImageURL {
                    AsyncImage(url: url) { phase in
                        switch phase {
                        case .success(let img): img.resizable().scaledToFill()
                        default: domainInitial
                        }
                    }
                } else {
                    domainInitial
                }
            }
            .frame(height: 100)
            .clipped()

            VStack(alignment: .leading, spacing: BrieflySpacing.s1) {
                Text(item.displayTitle)
                    .font(.brieflyBodySm)
                    .foregroundStyle(Color.brieflyTextPrimary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)

                Text("\(item.url.normalizedDomain) · \(item.savedAt.recentRelative)")
                    .font(.brieflyCaption)
                    .foregroundStyle(Color.brieflyInk400)
                    .lineLimit(1)
            }
            .padding(BrieflySpacing.s2)
        }
        .frame(width: 160)
        .background(Color.brieflyBgSurface)
        .clipShape(RoundedRectangle(cornerRadius: BrieflyRadius.md))
        .overlay(
            RoundedRectangle(cornerRadius: BrieflyRadius.md)
                .stroke(Color.brieflyBorder, lineWidth: 1)
        )
        .brieflyShadow1()
    }

    private var domainInitial: some View {
        Text(String(item.url.normalizedDomain.prefix(1)).uppercased())
            .font(.system(size: 28, weight: .semibold))
            .foregroundStyle(Color.brieflyInk300)
    }
}

private extension Date {
    var recentRelative: String {
        let f = RelativeDateTimeFormatter()
        f.locale = Locale.current
        f.unitsStyle = .abbreviated
        return f.localizedString(for: self, relativeTo: Date())
    }
}

#Preview {
    NavigationStack { SearchView() }
}

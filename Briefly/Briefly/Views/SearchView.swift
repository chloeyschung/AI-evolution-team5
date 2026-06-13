import SwiftUI

private enum FilterDropdown: Equatable {
    case category, platform
}

struct SearchView: View {
    @State private var query = ""
    @State private var selectedCategories: Set<String> = []
    @State private var selectedDomains: Set<String>    = []
    @State private var activeDropdown: FilterDropdown? = nil

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

    // MARK: - Localization

    private var isKorean: Bool {
        Locale.current.language.languageCode?.identifier == "ko"
    }

    private func L(_ ko: String, _ en: String) -> String { isKorean ? ko : en }

    private func categoryLabel(_ value: String) -> String {
        guard isKorean else { return value }
        switch value {
        case "Tech":      return "기술"
        case "Business":  return "비즈니스"
        case "Essays":    return "에세이"
        case "Research":  return "연구"
        case "Lifestyle": return "라이프스타일"
        case "News":      return "뉴스"
        case "Culture":   return "문화"
        case "Other":     return "기타"
        default:          return value
        }
    }

    // MARK: - Chip Labels

    private var categoryChipLabel: String {
        if selectedCategories.isEmpty { return L("카테고리", "Category") }
        return selectedCategories.sorted().map { categoryLabel($0) }.joined(separator: ", ")
    }

    private var domainChipLabel: String {
        if selectedDomains.isEmpty { return L("플랫폼", "Platform") }
        return selectedDomains.sorted().joined(separator: ", ")
    }

    // MARK: - Filter UI

    private var filterChipRow: some View {
        HStack(spacing: 8) {
            FilterDropdownChip(
                label: categoryChipLabel,
                isActive: !selectedCategories.isEmpty,
                isOpen: activeDropdown == .category
            ) {
                withAnimation(.easeInOut(duration: 0.15)) {
                    activeDropdown = activeDropdown == .category ? nil : .category
                }
            }

            FilterDropdownChip(
                label: domainChipLabel,
                isActive: !selectedDomains.isEmpty,
                isOpen: activeDropdown == .platform
            ) {
                withAnimation(.easeInOut(duration: 0.15)) {
                    activeDropdown = activeDropdown == .platform ? nil : .platform
                }
            }

            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
    }

    @ViewBuilder
    private var dropdownContent: some View {
        if let active = activeDropdown {
            ZStack(alignment: .topLeading) {
                Color.clear
                    .contentShape(Rectangle())
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .onTapGesture {
                        withAnimation(.easeInOut(duration: 0.15)) {
                            activeDropdown = nil
                        }
                    }

                dropdownCard(for: active)
                    .frame(maxWidth: 220, alignment: .leading)
                    .padding(.horizontal, 16)
                    .padding(.top, 4)
                    .transition(.opacity.combined(with: .scale(scale: 0.95, anchor: .topLeading)))
            }
        }
    }

    private func dropdownCard(for kind: FilterDropdown) -> some View {
        let items: [String] = kind == .category ? availableCategories : availableDomains
        let selectedSet: Set<String> = kind == .category ? selectedCategories : selectedDomains
        let makeLabel: (String) -> String = kind == .category ? { categoryLabel($0) } : { $0 }

        return VStack(alignment: .leading, spacing: 0) {
            Button {
                withAnimation(.easeInOut(duration: 0.15)) {
                    if kind == .category { selectedCategories = [] } else { selectedDomains = [] }
                    activeDropdown = nil
                }
            } label: {
                HStack {
                    Text(L("전체", "All"))
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(selectedSet.isEmpty ? Color.brieflyPrimary500 : Color.brieflyTextPrimary)
                    Spacer()
                    if selectedSet.isEmpty {
                        Image(systemName: "checkmark")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(Color.brieflyPrimary500)
                    }
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 11)
            }
            .buttonStyle(.plain)

            ForEach(items, id: \.self) { item in
                Divider().padding(.horizontal, 8)
                Button {
                    withAnimation(.easeInOut(duration: 0.15)) {
                        if kind == .category {
                            if selectedCategories.contains(item) { selectedCategories.remove(item) }
                            else { selectedCategories.insert(item) }
                        } else {
                            if selectedDomains.contains(item) { selectedDomains.remove(item) }
                            else { selectedDomains.insert(item) }
                        }
                    }
                } label: {
                    HStack {
                        Text(makeLabel(item))
                            .font(.system(size: 14))
                            .foregroundStyle(selectedSet.contains(item) ? Color.brieflyPrimary500 : Color.brieflyTextPrimary)
                        Spacer()
                        if selectedSet.contains(item) {
                            Image(systemName: "checkmark")
                                .font(.system(size: 12, weight: .semibold))
                                .foregroundStyle(Color.brieflyPrimary500)
                        }
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 11)
                }
                .buttonStyle(.plain)
            }
        }
        .background(Color.brieflyBgSurface)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.12), radius: 8, x: 0, y: 4)
    }

    // MARK: - Body

    var body: some View {
        VStack(spacing: 0) {
            filterChipRow
            Group {
                if !hasActiveSearch {
                    emptyPrompt
                } else if results.isEmpty {
                    noResults
                } else {
                    resultList
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .overlay(alignment: .topLeading) {
                dropdownContent
            }
        }
        .background(Color.brieflyBgApp.ignoresSafeArea())
        .navigationTitle("Search")
        .navigationBarTitleDisplayMode(.large)
        .searchable(text: $query, prompt: "제목, 키워드, 본문 검색...")
        .navigationDestination(for: SavedItem.self) { item in
            ItemDetailView(items: [item], startIndex: 0, showActions: true)
        }
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

#Preview {
    NavigationStack { SearchView() }
}

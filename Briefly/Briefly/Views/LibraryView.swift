import SwiftUI

// MARK: - Enums

enum LibraryFilter: String, CaseIterable {
    case inbox    = "Inbox"
    case archived = "Saved"
    case deleted  = "Discarded"
}

private enum FilterDropdown: Equatable {
    case category, platform
}

struct InboxNavigation: Hashable {
    let items: [SavedItem]
    let startIndex: Int

    static func == (lhs: InboxNavigation, rhs: InboxNavigation) -> Bool {
        lhs.startIndex == rhs.startIndex && lhs.items.map(\.id) == rhs.items.map(\.id)
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(startIndex)
        items.forEach { hasher.combine($0.id) }
    }
}

// MARK: - LibraryView

struct LibraryView: View {
    @StateObject private var viewModel = SavedItemsViewModel()
    @State private var selectedFilter: LibraryFilter = .inbox
    @State private var path = NavigationPath()
    @State private var pendingDeepLinkURL: URL?
    @State private var selectedCategories: Set<String> = []
    @State private var selectedDomains: Set<String>    = []
    @State private var activeDropdown: FilterDropdown? = nil
    @Environment(\.scenePhase) private var scenePhase

    // MARK: - Data

    private var tabItems: [SavedItem] {
        switch selectedFilter {
        case .inbox:    return viewModel.items.filter { $0.status == .unread }
        case .archived: return viewModel.items.filter { $0.status == .kept || $0.status == .read || $0.status == .discarded }
        case .deleted:  return viewModel.items.filter { $0.status == .deleted }
        }
    }

    private var displayedItems: [SavedItem] {
        tabItems
            .filter { selectedCategories.isEmpty || ($0.autoTagCategory.map { selectedCategories.contains($0) } ?? false) }
            .filter { selectedDomains.isEmpty || selectedDomains.contains($0.url.normalizedDomain) }
    }

    private var availableCategories: [String] {
        Array(Set(viewModel.items.compactMap(\.autoTagCategory))).sorted()
    }

    private var availableDomains: [String] {
        Array(Set(viewModel.items.map { $0.url.normalizedDomain })).sorted()
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

    // MARK: - Subviews

    private var titleHeaderView: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Text(selectedFilter.rawValue)
                .font(.largeTitle.bold())
                .foregroundStyle(Color.brieflyTextPrimary)
            if !displayedItems.isEmpty {
                Text("\(displayedItems.count)")
                    .font(.largeTitle.bold())
                    .foregroundStyle(Color.brieflyPrimary500)
            }
            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
    }

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
        .padding(.bottom, 8)
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
        NavigationStack(path: $path) {
            VStack(spacing: 0) {
                titleHeaderView
                filterChipRow
                ZStack(alignment: .bottom) {

                    // MARK: Content
                    if displayedItems.isEmpty {
                        emptyView
                    } else {
                        ScrollView {
                            LazyVStack(spacing: 0) {
                                ForEach(Array(displayedItems.enumerated()), id: \.element.id) { index, item in
                                    if selectedFilter == .inbox {
                                        NavigationLink(value: InboxNavigation(items: displayedItems, startIndex: index)) {
                                            LibraryCardView(item: item)
                                        }
                                        .buttonStyle(.plain)
                                    } else {
                                        NavigationLink(value: item) {
                                            LibraryCardView(item: item)
                                        }
                                        .buttonStyle(.plain)
                                    }

                                    Divider()
                                        .overlay(Color.brieflyBorder)
                                        .padding(.leading, 16)
                                }
                            }
                            .padding(.bottom, 80)
                        }
                    }

                    // MARK: Floating Filter Tab
                    HStack(spacing: 2) {
                        ForEach(LibraryFilter.allCases, id: \.self) { filter in
                            Button {
                                withAnimation(.easeInOut(duration: 0.2)) {
                                    selectedFilter = filter
                                    activeDropdown = nil
                                }
                            } label: {
                                Text(filter.rawValue)
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundStyle(selectedFilter == filter ? Color.brieflyTextPrimary : Color.brieflyInk400)
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 9)
                                    .background(
                                        selectedFilter == filter
                                            ? Color.brieflyBgSurface
                                            : Color.clear
                                    )
                                    .clipShape(Capsule())
                            }
                        }
                    }
                    .padding(4)
                    .background(Color.brieflyBgApp.opacity(0.92), in: Capsule())
                    .brieflyShadow3()
                    .padding(.bottom, 20)
                }
                .overlay(alignment: .topLeading) {
                    dropdownContent
                }
            } // VStack
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: InboxNavigation.self) { nav in
                ItemDetailView(items: nav.items, startIndex: nav.startIndex, showActions: true)
            }
            .navigationDestination(for: SavedItem.self) { item in
                ItemDetailView(items: [item], startIndex: 0, showActions: false)
            }
            .onAppear { viewModel.reload() }
            .onChange(of: scenePhase) { newPhase in
                if newPhase == .active { viewModel.reload() }
            }
            .onChange(of: viewModel.items) { items in
                if let url = pendingDeepLinkURL,
                   let item = items.first(where: { $0.url == url }) {
                    openItemAsInboxReader(item)
                    pendingDeepLinkURL = nil
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: .fetchCoordinatorDidUpdate)) { _ in
                viewModel.reload()
            }
            .onReceive(NotificationCenter.default.publisher(for: .brieflyOpenItem)) { notification in
                guard let url = notification.object as? URL else { return }
                viewModel.reload()
                if let item = viewModel.items.first(where: { $0.url == url }) {
                    openItemAsInboxReader(item)
                } else {
                    pendingDeepLinkURL = url
                }
            }
        }
    }

    private func openItemAsInboxReader(_ item: SavedItem) {
        guard item.status == .unread else {
            path.append(item)
            return
        }
        let inboxItems = viewModel.items.filter { $0.status == .unread }
        guard !inboxItems.isEmpty else { path.append(item); return }
        let startIndex = inboxItems.firstIndex(where: { $0.id == item.id }) ?? 0
        path.append(InboxNavigation(items: inboxItems, startIndex: startIndex))
    }

    private var emptyView: some View {
        let (icon, title, subtitle): (String, String, String) = {
            switch selectedFilter {
            case .inbox:
                return ("tray", "Inbox가 비어있어요", "공유하기 → Save Document to Briefly 로\n링크를 저장해보세요")
            case .archived:
                return ("archivebox", "Saved가 비어있어요", "Inbox에서 Keep한 링크가 여기에 표시됩니다")
            case .deleted:
                return ("trash", "Discarded가 비어있어요", "Inbox에서 Discard한 링크가 여기에 표시됩니다")
            }
        }()

        return VStack(spacing: BrieflySpacing.s4) {
            Image(systemName: icon)
                .font(.system(size: 48))
                .foregroundStyle(Color.brieflyInk300)
            Text(title)
                .font(.brieflyH2)
                .foregroundStyle(Color.brieflyTextPrimary)
            Text(subtitle)
                .font(.brieflyBody)
                .foregroundStyle(Color.brieflyTextSecondary)
                .multilineTextAlignment(.center)
        }
        .padding(BrieflySpacing.s6)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.brieflyBgApp.ignoresSafeArea())
    }
}

// MARK: - FilterDropdownChip

struct FilterDropdownChip: View {
    let label: String
    let isActive: Bool
    let isOpen: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 4) {
                Text(label)
                    .font(.system(size: 13, weight: .medium))
                    .lineLimit(1)
                Image(systemName: isOpen ? "chevron.up" : "chevron.down")
                    .font(.system(size: 10, weight: .semibold))
            }
            .foregroundStyle(isActive || isOpen ? Color.white : Color.brieflyTextPrimary)
            .padding(.horizontal, 12)
            .padding(.vertical, 7)
            .background(isActive || isOpen ? Color.brieflyPrimary500 : Color.brieflyBgSurface)
            .clipShape(Capsule())
            .overlay(
                Capsule().stroke(
                    isActive || isOpen ? Color.clear : Color.brieflyBorder,
                    lineWidth: 1
                )
            )
        }
        .buttonStyle(.plain)
        .animation(.easeInOut(duration: 0.15), value: isActive)
        .animation(.easeInOut(duration: 0.15), value: isOpen)
    }
}

// MARK: - Card

struct LibraryCardView: View {
    let item: SavedItem

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {

            // ── 출처 행 ──────────────────────────────────────
            HStack(spacing: 6) {
                AsyncImage(url: faviconURL) { image in
                    image.resizable().scaledToFill()
                } placeholder: {
                    RoundedRectangle(cornerRadius: 3)
                        .fill(Color.brieflyInk200)
                }
                .frame(width: 16, height: 16)
                .clipShape(RoundedRectangle(cornerRadius: 3))

                Text(item.siteName?.uppercased() ?? item.domain.uppercased())
                    .font(.brieflyMeta)
                    .foregroundStyle(Color.brieflyInk400)

                Spacer()

                fetchStatusBadge
            }

            // ── 제목 + 썸네일 ─────────────────────────────────
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(item.displayTitle)
                        .font(.brieflyH4)
                        .foregroundStyle(Color.brieflyTextPrimary)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)

                    Text(item.savedAt.libraryDateString)
                        .font(.brieflyMeta)
                        .foregroundStyle(Color.brieflyInk400)

                    Text(item.ogDescription ?? "AI 요약이 준비 중입니다")
                        .font(.brieflyBodySm)
                        .foregroundStyle(Color.brieflyTextSecondary)
                        .lineLimit(3)

                    if !item.autoTagKeywordsEn.isEmpty {
                        KeywordPillRow(keywords: item.autoTagKeywordsEn, maxCount: 3)
                            .padding(.top, 2)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                Group {
                    if let imageURL = item.ogImageURL {
                        AsyncImage(url: imageURL) { phase in
                            switch phase {
                            case .success(let image):
                                image.resizable().scaledToFill()
                            default:
                                thumbnailPlaceholder
                            }
                        }
                    } else {
                        thumbnailPlaceholder
                    }
                }
                .frame(width: 80, height: 80)
                .clipShape(RoundedRectangle(cornerRadius: BrieflyRadius.sm))
            }
        }
        .padding(16)
        .contentShape(Rectangle())
    }

    var faviconURL: URL? {
        URL(string: "https://www.google.com/s2/favicons?domain=\(item.domain)&sz=64")
    }

    @ViewBuilder
    var fetchStatusBadge: some View {
        switch item.fetchStatus {
        case .fetching:
            ProgressView().scaleEffect(0.7)
        case .failed:
            Image(systemName: "exclamationmark.circle")
                .font(.caption)
                .foregroundStyle(Color.brieflyError.opacity(0.7))
        case .partial:
            Image(systemName: "exclamationmark.circle")
                .font(.caption)
                .foregroundStyle(Color.brieflyWarning.opacity(0.7))
        default:
            Image(systemName: "ellipsis")
                .foregroundStyle(Color.brieflyInk400)
                .font(.subheadline)
        }
    }

    var thumbnailPlaceholder: some View {
        RoundedRectangle(cornerRadius: BrieflyRadius.sm)
            .fill(Color.brieflyInk100)
            .overlay {
                Image(systemName: "photo")
                    .foregroundStyle(Color.brieflyInk300)
                    .font(.brieflyH3)
            }
    }
}

// MARK: - Date Helper

extension Date {
    var libraryDateString: String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US")
        formatter.dateFormat = "MMM d"
        return formatter.string(from: self)
    }
}

// MARK: - Preview

#Preview {
    LibraryView()
}

import SwiftUI

// MARK: - Filter

enum LibraryFilter: String, CaseIterable {
    case inbox    = "Inbox"
    case archived = "Saved"
    case deleted  = "Discarded"
}

// Inbox 카드 리더 진입 시 전체 목록과 시작 인덱스를 함께 전달
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
    @Environment(\.scenePhase) private var scenePhase

    private var filteredItems: [SavedItem] {
        switch selectedFilter {
        case .inbox:    return viewModel.items.filter { $0.status == .unread }
        case .archived: return viewModel.items.filter { $0.status == .kept || $0.status == .read || $0.status == .discarded }
        case .deleted:  return viewModel.items.filter { $0.status == .deleted }
        }
    }

    private var navigationTitle: String {
        switch selectedFilter {
        case .inbox:
            return filteredItems.isEmpty ? "Inbox" : "Inbox \(filteredItems.count)"
        case .archived:
            return "Saved"
        case .deleted:
            return "Discarded"
        }
    }

    var body: some View {
        NavigationStack(path: $path) {
            ZStack(alignment: .bottom) {

                // MARK: Content
                if filteredItems.isEmpty {
                    emptyView
                } else {
                    ScrollView {
                        LazyVStack(spacing: 0) {
                            ForEach(Array(filteredItems.enumerated()), id: \.element.id) { index, item in
                                if selectedFilter == .inbox {
                                    NavigationLink(value: InboxNavigation(items: filteredItems, startIndex: index)) {
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
                            }
                        } label: {
                            Text(filter.rawValue)
                                .font(.subheadline.weight(.semibold))
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
            .navigationTitle(navigationTitle)
            .navigationBarTitleDisplayMode(.large)
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
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                // 썸네일 — OG Image (없으면 placeholder)
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

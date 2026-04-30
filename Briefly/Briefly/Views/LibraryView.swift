import SwiftUI

// MARK: - Filter

enum LibraryFilter: String, CaseIterable {
    case inbox   = "Inbox"
    case archive = "Archive"
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
        case .inbox:   return viewModel.items.filter { $0.status == .unread }
        case .archive: return viewModel.items.filter { $0.status != .unread }
        }
    }

    private var navigationTitle: String {
        switch selectedFilter {
        case .inbox:
            return filteredItems.isEmpty ? "Inbox" : "Inbox \(filteredItems.count)"
        case .archive:
            return "Archive"
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
                            ForEach(filteredItems) { item in
                                NavigationLink(value: item) {
                                    LibraryCardView(item: item)
                                }
                                .buttonStyle(.plain)

                                Divider()
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
                                .foregroundStyle(selectedFilter == filter ? .primary : .secondary)
                                .padding(.horizontal, 24)
                                .padding(.vertical, 9)
                                .background(
                                    selectedFilter == filter
                                        ? Color(.systemBackground)
                                        : Color.clear
                                )
                                .clipShape(Capsule())
                        }
                    }
                }
                .padding(4)
                .background(.regularMaterial, in: Capsule())
                .shadow(color: .black.opacity(0.12), radius: 10, y: 4)
                .padding(.bottom, 20)
            }
            .navigationTitle(navigationTitle)
            .navigationBarTitleDisplayMode(.large)
            .navigationDestination(for: SavedItem.self) { item in
                ItemDetailView(item: item)
            }
            .onAppear { viewModel.reload() }
            .onChange(of: scenePhase) { newPhase in
                if newPhase == .active { viewModel.reload() }
            }
            .onChange(of: viewModel.items) { items in
                // 딥링크로 열려야 할 아이템이 아직 로드 안됐다가 이제 로드된 경우
                if let url = pendingDeepLinkURL,
                   let item = items.first(where: { $0.url == url }) {
                    path.append(item)
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
                    path.append(item)
                } else {
                    // 아직 items에 없으면 (drainInbox 완료 전) 대기
                    pendingDeepLinkURL = url
                }
            }
        }
    }

    private var emptyView: some View {
        VStack(spacing: 16) {
            Image(systemName: selectedFilter == .inbox ? "tray" : "archivebox")
                .font(.system(size: 60))
                .foregroundStyle(.secondary)
            Text(selectedFilter == .inbox ? "Inbox가 비어있어요" : "Archive가 비어있어요")
                .font(.headline)
            Text("공유하기 → Save Document to Briefly 로\n링크를 저장해보세요")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
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
                        .fill(Color.secondary.opacity(0.25))
                }
                .frame(width: 16, height: 16)
                .clipShape(RoundedRectangle(cornerRadius: 3))

                Text(item.siteName?.uppercased() ?? item.domain.uppercased())
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)

                Spacer()

                fetchStatusBadge
            }

            // ── 제목 + 썸네일 ─────────────────────────────────
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(item.displayTitle)
                        .font(.body.weight(.semibold))
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)

                    Text(item.savedAt.libraryDateString)
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    Text(item.ogDescription ?? "AI 요약이 준비 중입니다")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
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
                .clipShape(RoundedRectangle(cornerRadius: 8))
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
                .foregroundStyle(.red.opacity(0.6))
        case .partial:
            Image(systemName: "exclamationmark.circle")
                .font(.caption)
                .foregroundStyle(.orange.opacity(0.6))
        default:
            Image(systemName: "ellipsis")
                .foregroundStyle(.secondary)
                .font(.subheadline)
        }
    }

    var thumbnailPlaceholder: some View {
        RoundedRectangle(cornerRadius: 8)
            .fill(Color.secondary.opacity(0.12))
            .overlay {
                Image(systemName: "photo")
                    .foregroundStyle(.secondary.opacity(0.4))
                    .font(.title3)
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

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
        ZStack(alignment: .bottom) {
            // MARK: Content
            if filteredItems.isEmpty {
                emptyView
            } else {
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(filteredItems) { item in
                            NavigationLink(destination: ItemDetailView(item: item)) {
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
        .onAppear { viewModel.reload() }
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

                Text(item.domain.uppercased())
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)

                Spacer()

                Image(systemName: "ellipsis")
                    .foregroundStyle(.secondary)
                    .font(.subheadline)
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

                    Text("AI 요약이 준비 중입니다")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(3)
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                // 썸네일 — 우측 고정 (Phase 2에서 OG Image로 교체 예정)
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.secondary.opacity(0.12))
                    .overlay {
                        Image(systemName: "photo")
                            .foregroundStyle(.secondary.opacity(0.4))
                            .font(.title3)
                    }
                    .frame(width: 80, height: 80)
            }
        }
        .padding(16)
        .contentShape(Rectangle())
    }

    var faviconURL: URL? {
        URL(string: "https://www.google.com/s2/favicons?domain=\(item.domain)&sz=64")
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
    NavigationStack { LibraryView() }
}

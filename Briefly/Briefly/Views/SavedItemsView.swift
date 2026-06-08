import SwiftUI

@MainActor
final class SavedItemsViewModel: ObservableObject {
    @Published var items: [SavedItem] = []
    private var isFetchingKeywords = false

    func reload() {
        items = StorageService.shared.drainInboxAndLoad()
        fetchMissingKeywords()
    }

    func markAsRead(_ item: SavedItem) {
        var updated = item
        updated.status = .read
        StorageService.shared.updateItem(updated)
        if let idx = items.firstIndex(where: { $0.id == item.id }) {
            items[idx] = updated
        }
    }

    // serverContentId가 있지만 keywords가 비어있는 항목을 백그라운드에서 패치
    private func fetchMissingKeywords() {
        guard !isFetchingKeywords else { return }
        guard let token = AuthTokenStore.shared.accessToken else { return }
        let pending = items.filter { $0.serverContentId != nil && $0.autoTagKeywordsEn.isEmpty }
        guard !pending.isEmpty else { return }

        isFetchingKeywords = true
        Task {
            defer { isFetchingKeywords = false }
            for item in pending {
                guard let contentId = item.serverContentId else { continue }
                if let detail = try? await BrieflyAPI.shared.fetchContentDetail(contentId: contentId, token: token),
                   !detail.autoTagKeywordsEn.isEmpty {
                    StorageService.shared.updateAutoTags(
                        for: item.id,
                        category: detail.autoTagCategory,
                        keywordsEn: detail.autoTagKeywordsEn,
                        keywordsOriginal: detail.autoTagKeywordsOriginal
                    )
                }
            }
            reload()
        }
    }
}

// MARK: - View

struct SavedItemsView: View {
    @ObservedObject var viewModel: SavedItemsViewModel

    var body: some View {
        Group {
            if viewModel.items.isEmpty {
                emptyStateView
            } else {
                listView
            }
        }
        .background(Color.brieflyBgApp.ignoresSafeArea())
        .navigationTitle("Briefly")
        .navigationBarTitleDisplayMode(.large)
        .onAppear { viewModel.reload() }
    }

    // MARK: - Empty State

    private var emptyStateView: some View {
        VStack(spacing: BrieflySpacing.s4) {
            Image(systemName: "link.circle")
                .font(.system(size: 48))
                .foregroundStyle(Color.brieflyInk300)

            Text("아직 저장된 링크가 없어요")
                .font(.brieflyH2)
                .foregroundStyle(Color.brieflyTextPrimary)

            Text("Safari에서 기사를 보다가\n공유 버튼 → Briefly를 탭해보세요")
                .font(.brieflyBody)
                .foregroundStyle(Color.brieflyTextSecondary)
                .multilineTextAlignment(.center)
        }
        .padding()
    }

    // MARK: - List

    private var listView: some View {
        List(viewModel.items) { item in
            ItemRowView(item: item)
                .contentShape(Rectangle())
                .onTapGesture {
                    UIApplication.shared.open(item.url)
                    viewModel.markAsRead(item)
                }
                .listRowBackground(Color.brieflyBgApp)
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Color.brieflyBgApp)
        .refreshable {
            viewModel.reload()
        }
    }
}

// MARK: - Row

private struct ItemRowView: View {
    let item: SavedItem

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Circle()
                .fill(item.status == .unread ? Color.brieflyPrimary500 : Color.clear)
                .frame(width: 8, height: 8)
                .padding(.top, 6)

            VStack(alignment: .leading, spacing: 4) {
                Text(item.displayTitle)
                    .font(.brieflyBody)
                    .foregroundStyle(Color.brieflyTextPrimary)
                    .lineLimit(1)

                Text("\(item.domain) · \(item.savedAt.relativeString)")
                    .font(.brieflyMeta)
                    .foregroundStyle(Color.brieflyInk400)

                if !item.autoTagKeywordsEn.isEmpty {
                    KeywordPillRow(keywords: item.autoTagKeywordsEn, maxCount: 3)
                        .padding(.top, 2)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Date Extension

private extension Date {
    var relativeString: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.locale = Locale(identifier: "ko_KR")
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: self, relativeTo: Date())
    }
}

#Preview {
    NavigationStack {
        SavedItemsView(viewModel: SavedItemsViewModel())
    }
}

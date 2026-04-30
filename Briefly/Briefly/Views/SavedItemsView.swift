import SwiftUI

@MainActor
final class SavedItemsViewModel: ObservableObject {
    @Published var items: [SavedItem] = []

    func reload() {
        items = StorageService.shared.drainInboxAndLoad()
    }

    func markAsRead(_ item: SavedItem) {
        var updated = item
        updated.status = .read
        StorageService.shared.updateItem(updated)
        if let idx = items.firstIndex(where: { $0.id == item.id }) {
            items[idx] = updated
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
        .navigationTitle("Briefly")
        .navigationBarTitleDisplayMode(.large)
        .onAppear { viewModel.reload() }
    }

    // MARK: - Empty State

    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "link.circle")
                .font(.system(size: 60))
                .foregroundStyle(.secondary)

            Text("아직 저장된 링크가 없어요")
                .font(.headline)

            Text("Safari에서 기사를 보다가\n공유 버튼 → Briefly를 탭해보세요")
                .font(.subheadline)
                .foregroundStyle(.secondary)
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
        }
        .listStyle(.plain)
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
                .fill(item.status == .unread ? Color.accentColor : Color.clear)
                .frame(width: 8, height: 8)
                .padding(.top, 6)

            VStack(alignment: .leading, spacing: 4) {
                Text(item.displayTitle)
                    .font(.body)
                    .lineLimit(1)

                Text("\(item.domain) · \(item.savedAt.relativeString)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
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

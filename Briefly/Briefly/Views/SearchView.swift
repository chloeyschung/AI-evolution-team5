import SwiftUI

struct SearchView: View {
    @State private var query = ""

    private var trimmed: String { query.trimmingCharacters(in: .whitespaces) }

    private var results: [SavedItem] {
        guard !trimmed.isEmpty else { return [] }
        let q = trimmed.lowercased()
        return StorageService.shared.loadAll()
            .filter { $0.status != .deleted }
            .filter { item in
                item.displayTitle.lowercased().contains(q) ||
                (item.ogDescription?.lowercased().contains(q) ?? false) ||
                (item.summary?.lowercased().contains(q) ?? false) ||
                (item.articleText?.lowercased().contains(q) ?? false) ||
                item.autoTagKeywordsEn.contains { $0.lowercased().contains(q) } ||
                item.autoTagKeywordsOriginal.contains { $0.lowercased().contains(q) } ||
                (item.autoTagCategory?.lowercased().contains(q) ?? false) ||
                (item.url.host?.lowercased().contains(q) ?? false)
            }
            .sorted { $0.savedAt > $1.savedAt }
    }

    var body: some View {
        Group {
            if trimmed.isEmpty {
                emptyPrompt
            } else if results.isEmpty {
                noResults
            } else {
                resultList
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
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
            Text("'\(trimmed)'에 대한 결과가 없습니다")
                .font(.brieflyH2)
                .foregroundStyle(Color.brieflyTextPrimary)
                .multilineTextAlignment(.center)
            Text("다른 키워드로 검색해보세요")
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

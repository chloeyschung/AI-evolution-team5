import SwiftUI

struct HomeView: View {
    @ObservedObject var viewModel: HomeViewModel
    @State private var selectedSavedItem: SavedItem? = nil

    var body: some View {
        ZStack {
            Color.brieflyBgApp.ignoresSafeArea()
            if viewModel.sections.isEmpty {
                emptyStateView
            } else {
                contentView
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(isPresented: Binding(
            get: { selectedSavedItem != nil },
            set: { if !$0 { selectedSavedItem = nil } }
        )) {
            if let item = selectedSavedItem {
                ItemDetailView(items: [item], startIndex: 0, showActions: true)
            }
        }
    }

    private var contentView: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: BrieflySpacing.s8) {
                Image("logo_full")
                    .resizable()
                    .scaledToFit()
                    .frame(height: 36)
                    .padding(.horizontal, BrieflySpacing.s4)
                    .padding(.top, BrieflySpacing.s2)
                ForEach(viewModel.sections) { section in
                    HomeSectionView(section: section) { item in
                        switch item {
                        case .local(let savedItem):
                            selectedSavedItem = savedItem
                        case .server(let content):
                            selectedSavedItem = SavedItem(serverContent: content)
                        }
                    }
                }
            }
            .padding(.vertical, BrieflySpacing.s4)
        }
        .refreshable { viewModel.reload() }
    }

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
}

#Preview {
    NavigationStack {
        HomeView(viewModel: HomeViewModel())
    }
}

private extension SavedItem {
    init(serverContent: ServerContent) {
        self.id = UUID()
        self.url = serverContent.url
        self.title = serverContent.title
        self.savedAt = serverContent.createdAt
        self.status = .unread
        self.serverContentId = serverContent.id
        self.ogTitle = serverContent.title
        self.ogImageURL = serverContent.thumbnailURL
        self.ogDescription = nil
        self.siteName = nil
        self.articleText = nil
        self.fetchStatus = .done
        self.summary = serverContent.summary
        self.summaryStatus = serverContent.summary != nil ? .done : .unknown
        self.autoTagCategory = serverContent.autoTagCategory
        self.autoTagKeywordsEn = serverContent.autoTagKeywordsEn
        self.autoTagKeywordsOriginal = serverContent.autoTagKeywordsOriginal
    }
}

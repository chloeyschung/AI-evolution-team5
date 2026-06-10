import SwiftUI

struct HomeView: View {
    @ObservedObject var viewModel: HomeViewModel

    var body: some View {
        ZStack {
            Color.brieflyBgApp.ignoresSafeArea()
            if viewModel.sections.isEmpty {
                emptyStateView
            } else {
                contentView
            }
        }
        .navigationTitle("Briefly")
        .navigationBarTitleDisplayMode(.large)
    }

    private var contentView: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: BrieflySpacing.s8) {
                ForEach(viewModel.sections) { section in
                    HomeSectionView(section: section) { item in
                        UIApplication.shared.open(item.url)
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

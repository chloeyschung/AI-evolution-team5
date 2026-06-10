import SwiftUI

struct HomeSectionView: View {
    let section: HomeCardSection
    let onItemTap: (HomeItem) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: BrieflySpacing.s3) {
            headerView
            carouselView
        }
    }

    private var headerView: some View {
        VStack(alignment: .leading, spacing: BrieflySpacing.s1) {
            HStack(spacing: 6) {
                Text(section.icon)
                    .font(.system(size: 16))
                Text(section.title)
                    .font(.title3)
                    .fontWeight(.bold)
                    .foregroundStyle(Color.brieflyTextPrimary)
            }
            if let subtitle = section.subtitle, !subtitle.isEmpty {
                Text(subtitle)
                    .font(.brieflyCaption)
                    .foregroundStyle(Color.brieflyTextSecondary)
            }
        }
        .padding(.horizontal, BrieflySpacing.s4)
    }

    @ViewBuilder
    private var carouselView: some View {
        if case .topicPlaceholder = section.kind {
            placeholderView
        } else {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: BrieflySpacing.s3) {
                    ForEach(section.items) { item in
                        ContentCardView(item: item) { onItemTap(item) }
                    }
                }
                .padding(.horizontal, BrieflySpacing.s4)
            }
        }
    }

    private var placeholderView: some View {
        HStack(spacing: BrieflySpacing.s2) {
            Image(systemName: "sparkles")
                .foregroundStyle(Color.brieflyInk300)
            Text("주제 분석 중...")
                .font(.brieflyBody)
                .foregroundStyle(Color.brieflyTextSecondary)
        }
        .padding(.horizontal, BrieflySpacing.s4)
        .padding(.vertical, BrieflySpacing.s3)
    }
}

import SwiftUI
import UIKit

struct ItemDetailView: View {
    let items: [SavedItem]
    let showActions: Bool

    @State private var currentIndex: Int
    @State private var dragOffset: CGFloat = 0
    @State private var cardScale: CGFloat = 1.0
    @State private var isProcessing = false
    @State private var isArticleExpanded = false
    @State private var showBrowser = false
    @Environment(\.dismiss) private var dismiss

    init(items: [SavedItem], startIndex: Int, showActions: Bool) {
        self.items = items
        self.showActions = showActions
        self._currentIndex = State(initialValue: startIndex)
    }

    var currentItem: SavedItem { items[currentIndex] }

    // MARK: - Body

    var body: some View {
        ZStack(alignment: .top) {
            Color(.systemGroupedBackground).ignoresSafeArea()

            // 외부 ScrollView — 카드 전체가 콘텐츠 높이만큼 늘어나며 스크롤됨
            ScrollView(.vertical, showsIndicators: false) {
                VStack(alignment: .leading, spacing: 0) {
                    thumbnailSection
                    contentSection
                }
                .background(Color(.systemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
                .shadow(color: .black.opacity(0.12), radius: 18, y: 6)
                .scaleEffect(cardScale)
                .padding(.horizontal, 12)
                .padding(.top, 4)
                .padding(.bottom, 12)
            }
            .offset(x: dragOffset)
            .rotationEffect(
                .degrees(Double(dragOffset) / Double(UIScreen.main.bounds.width) * 10.0),
                anchor: UnitPoint(x: 0.5, y: 0.9)
            )
            .simultaneousGesture(swipeGesture)

            // 스와이프 방향 인디케이터 (화면 고정, 스크롤 무관)
            if showActions {
                swipeIndicators.padding(.top, 8)
            }
        }
        .safeAreaInset(edge: .bottom) {
            if showActions { actionBar }
        }
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showBrowser) {
            SafariBrowserView(url: currentItem.url)
        }
    }

    @ViewBuilder
    private var swipeIndicators: some View {
        HStack {
            swipeBadge("DELETE", color: .red, degrees: -15,
                       opacity: dragOffset < -20 ? Double(min(1.0, abs(dragOffset) / 80.0)) : 0)
            Spacer()
            swipeBadge("KEEP", color: .green, degrees: 15,
                       opacity: dragOffset > 20 ? Double(min(1.0, abs(dragOffset) / 80.0)) : 0)
        }
        .padding(.top, 20)
        .padding(.horizontal, 20)
    }

    private func swipeBadge(_ label: String, color: Color, degrees: Double, opacity: Double) -> some View {
        Group { Text(label) }
            .font(.caption)
            .fontWeight(.black)
            .foregroundStyle(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .overlay(RoundedRectangle(cornerRadius: 6).stroke(color, lineWidth: 2.5))
            .rotationEffect(.degrees(degrees))
            .opacity(opacity)
    }

    // MARK: - Swipe Gesture

    private var swipeGesture: some Gesture {
        DragGesture(minimumDistance: 20)
            .onChanged { value in
                guard showActions, !isProcessing else { return }
                guard abs(value.translation.width) > abs(value.translation.height) else { return }
                dragOffset = value.translation.width
            }
            .onEnded { value in
                guard showActions, !isProcessing else { return }
                guard abs(value.translation.width) > abs(value.translation.height) else {
                    snapBack()
                    return
                }
                let w = value.translation.width
                if w > 100 { performKeep() }
                else if w < -100 { performDelete() }
                else { snapBack() }
            }
    }

    private func snapBack() {
        withAnimation(.spring(response: 0.35, dampingFraction: 0.7)) {
            dragOffset = 0
        }
    }

    // MARK: - Actions

    private func performKeep() {
        guard !isProcessing else { return }
        isProcessing = true

        var updated = currentItem
        updated.status = .kept
        StorageService.shared.updateItemById(updated)

        let itemId = currentItem.id
        if let token = AuthTokenStore.shared.accessToken {
            Task {
                let contentId = StorageService.shared.loadAll()
                    .first(where: { $0.id == itemId })?.serverContentId
                    ?? currentItem.serverContentId
                if let contentId {
                    try? await BrieflyAPI.shared.swipe(contentId: contentId, action: .keep, token: token)
                }
            }
        }

        flyOut(direction: 1)
    }

    private func performDelete() {
        guard !isProcessing else { return }
        isProcessing = true

        var updated = currentItem
        updated.status = .deleted
        StorageService.shared.updateItemById(updated)

        let itemId = currentItem.id
        if let token = AuthTokenStore.shared.accessToken {
            Task {
                let contentId = StorageService.shared.loadAll()
                    .first(where: { $0.id == itemId })?.serverContentId
                    ?? currentItem.serverContentId
                if let contentId {
                    try? await BrieflyAPI.shared.swipe(contentId: contentId, action: .discard, token: token)
                }
            }
        }

        flyOut(direction: -1)
    }

    private func performSkip() {
        guard !isProcessing else { return }
        isProcessing = true
        flyOut(direction: 1, isSkip: true)
    }

    private func flyOut(direction: CGFloat, isSkip: Bool = false) {
        let targetOffset = direction * CGFloat(UIScreen.main.bounds.width) * 1.6
        withAnimation(.easeIn(duration: 0.22)) {
            dragOffset = targetOffset
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            if !isSkip {
                NotificationCenter.default.post(name: .fetchCoordinatorDidUpdate, object: nil)
            }
            withAnimation(.none) { dragOffset = 0 }
            isArticleExpanded = false

            if currentIndex + 1 < items.count {
                withAnimation(.spring(response: 0.35, dampingFraction: 0.75)) {
                    cardScale = 0.94
                }
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
                    currentIndex += 1
                    withAnimation(.spring(response: 0.35, dampingFraction: 0.75)) {
                        cardScale = 1.0
                    }
                    isProcessing = false
                }
            } else {
                isProcessing = false
                dismiss()
            }
        }
    }

    // MARK: - Bottom Action Bar

    private var actionBar: some View {
        VStack(spacing: 0) {
            Divider()
            HStack(spacing: 0) {
                Button("Delete") { performDelete() }
                    .frame(maxWidth: .infinity)
                    .foregroundStyle(.red)

                Divider().frame(height: 22)

                Button("Skip Now") { performSkip() }
                    .frame(maxWidth: .infinity)
                    .foregroundStyle(.secondary)

                Divider().frame(height: 22)

                Button("Keep") { performKeep() }
                    .frame(maxWidth: .infinity)
                    .foregroundStyle(.blue)
            }
            .font(.subheadline.weight(.semibold))
            .padding(.vertical, 14)
            .background(Color(.systemBackground))
        }
        .disabled(isProcessing)
    }

    // MARK: - Content Sections

    private var thumbnailSection: some View {
        Group {
            if let imageURL = currentItem.ogImageURL {
                AsyncImage(url: imageURL) { phase in
                    switch phase {
                    case .success(let image): image.resizable().scaledToFill()
                    default: thumbnailPlaceholder
                    }
                }
            } else {
                thumbnailPlaceholder
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: 200)
        .clipped()
    }

    private var contentSection: some View {
        VStack(alignment: .leading, spacing: 20) {
            // 출처
            HStack(spacing: 8) {
                AsyncImage(url: faviconURL) { image in
                    image.resizable().scaledToFill()
                } placeholder: {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.secondary.opacity(0.25))
                }
                .frame(width: 20, height: 20)
                .clipShape(RoundedRectangle(cornerRadius: 4))

                Text(currentItem.siteName?.uppercased() ?? currentItem.domain.uppercased())
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
            }

            // 제목
            Text(currentItem.displayTitle)
                .font(.title2.weight(.bold))
                .fixedSize(horizontal: false, vertical: true)

            // 저장 날짜
            Label(currentItem.savedAt.detailDateString, systemImage: "calendar")
                .font(.caption)
                .foregroundStyle(.secondary)

            Divider()

            // AI 요약
            VStack(alignment: .leading, spacing: 10) {
                Label("AI 요약", systemImage: "sparkles")
                    .font(.subheadline.weight(.semibold))
                Text("AI 요약은 Phase 2b에서 추가될 예정입니다.\nClaude API를 통해 본문 핵심 내용을 최대 300자로 요약해 드립니다.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.secondary.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))

            // 본문
            articleSection

            Divider()

            // 원문 바로가기
            Button { showBrowser = true } label: {
                HStack {
                    Image(systemName: "safari")
                    Text("원문 바로가기")
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .font(.body.weight(.medium))
                .foregroundStyle(.blue)
                .padding(14)
                .background(Color.blue.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
            }

            Text(currentItem.url.absoluteString)
                .font(.caption2)
                .foregroundStyle(.tertiary)
                .lineLimit(2)
        }
        .padding(20)
    }

    @ViewBuilder
    private var articleSection: some View {
        switch currentItem.fetchStatus {
        case .pending, .fetching:
            HStack(spacing: 10) {
                ProgressView()
                Text("본문을 불러오는 중...")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.secondary.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))

        case .failed:
            EmptyView()

        case .done, .partial:
            if let text = currentItem.articleText, !text.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    HStack {
                        Label("본문", systemImage: "doc.text")
                            .font(.subheadline.weight(.semibold))
                        Spacer()
                        Button {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                isArticleExpanded.toggle()
                            }
                        } label: {
                            Text(isArticleExpanded ? "접기" : "펼치기")
                                .font(.caption)
                                .foregroundStyle(.blue)
                        }
                    }
                    Text(text)
                        .font(.body)
                        .foregroundStyle(.primary)
                        .lineLimit(isArticleExpanded ? nil : 6)
                        .fixedSize(horizontal: false, vertical: true)
                        .animation(.easeInOut(duration: 0.2), value: isArticleExpanded)
                }
                .padding(14)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.secondary.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
            }
        }
    }

    private var faviconURL: URL? {
        URL(string: "https://www.google.com/s2/favicons?domain=\(currentItem.domain)&sz=64")
    }

    private var thumbnailPlaceholder: some View {
        Rectangle()
            .fill(Color.secondary.opacity(0.1))
            .overlay {
                Image(systemName: "photo")
                    .font(.system(size: 40))
                    .foregroundStyle(.secondary.opacity(0.35))
            }
    }
}

// MARK: - Date Helper

private extension Date {
    var detailDateString: String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ko_KR")
        formatter.dateFormat = "yyyy년 M월 d일 저장"
        return formatter.string(from: self)
    }
}

#Preview {
    NavigationStack {
        ItemDetailView(
            items: [SavedItem(
                url: URL(string: "https://linkedin.com/post/example")!,
                title: "Carnegie Mellon University School of Computer Science's Post"
            )],
            startIndex: 0,
            showActions: true
        )
    }
}

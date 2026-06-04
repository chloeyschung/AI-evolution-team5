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
    @State private var isSummaryLoading = false
    @State private var loadedSummary: String? = nil
    @State private var liveItem: SavedItem? = nil
    @State private var summaryPollId = UUID()
    @State private var isRetrying = false
    @Environment(\.dismiss) private var dismiss

    init(items: [SavedItem], startIndex: Int, showActions: Bool) {
        self.items = items
        self.showActions = showActions
        self._currentIndex = State(initialValue: startIndex)
    }

    var currentItem: SavedItem { liveItem ?? items[currentIndex] }

    // MARK: - Body

    var body: some View {
        ZStack(alignment: .top) {
            Color.brieflyBgApp.ignoresSafeArea()

            // 외부 ScrollView — 카드 전체가 콘텐츠 높이만큼 늘어나며 스크롤됨
            ScrollView(.vertical, showsIndicators: false) {
                VStack(alignment: .leading, spacing: 0) {
                    thumbnailSection
                    contentSection
                }
                .background(Color.brieflyBgSurface)
                .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
                .brieflyShadow3()
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
        .toolbar {
            if showActions && items.count > 1 {
                ToolbarItem(placement: .principal) {
                    Text("\(currentIndex + 1) / \(items.count)")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(Color.brieflyInk400)
                }
            }
        }
        .sheet(isPresented: $showBrowser) {
            SafariBrowserView(url: currentItem.url)
        }
        .onChange(of: currentIndex) { _ in
            liveItem = nil
            summaryPollId = UUID()
        }
        .onReceive(NotificationCenter.default.publisher(for: .fetchCoordinatorDidUpdate)) { _ in
            let baseItem = items[currentIndex]
            if let updated = StorageService.shared.loadAll().first(where: { $0.id == baseItem.id }) {
                liveItem = updated
            }
        }
    }

    @ViewBuilder
    private var swipeIndicators: some View {
        HStack {
            swipeBadge("DISCARD", color: Color.brieflyError, degrees: -15,
                       opacity: dragOffset < -20 ? Double(min(1.0, abs(dragOffset) / 80.0)) : 0)
            Spacer()
            swipeBadge("KEEP", color: Color.brieflyPrimary500, degrees: 15,
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
        let itemURL = currentItem.url
        if let token = AuthTokenStore.shared.accessToken {
            Task {
                var contentId = StorageService.shared.loadAll()
                    .first(where: { $0.id == itemId })?.serverContentId
                    ?? currentItem.serverContentId
                // serverContentId가 없으면 먼저 서버에 업로드해서 id를 받아온 후 swipe
                if contentId == nil {
                    print("[Keep] serverContentId 없음 — share 먼저 시도: \(itemURL)")
                    do {
                        let result = try await BrieflyAPI.shared.share(url: itemURL, token: token)
                        contentId = result.id
                        var synced = updated
                        synced.serverContentId = result.id
                        StorageService.shared.updateItemById(synced)
                        print("[Keep] share 성공: contentId=\(result.id)")
                    } catch {
                        print("[Keep] share 실패: \(error.localizedDescription)")
                    }
                }
                if let contentId {
                    do {
                        try await BrieflyAPI.shared.swipe(contentId: contentId, action: .keep, token: token)
                        print("[Keep] swipe 성공: contentId=\(contentId)")
                    } catch {
                        print("[Keep] swipe 실패: \(error.localizedDescription)")
                    }
                } else {
                    print("[Keep] contentId 없음 — swipe 스킵")
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
        let itemURL = currentItem.url
        if let token = AuthTokenStore.shared.accessToken {
            Task {
                var contentId = StorageService.shared.loadAll()
                    .first(where: { $0.id == itemId })?.serverContentId
                    ?? currentItem.serverContentId
                // serverContentId가 없으면 먼저 서버에 업로드해서 id를 받아온 후 swipe
                if contentId == nil {
                    print("[Delete] serverContentId 없음 — share 먼저 시도: \(itemURL)")
                    do {
                        let result = try await BrieflyAPI.shared.share(url: itemURL, token: token)
                        contentId = result.id
                        var synced = updated
                        synced.serverContentId = result.id
                        StorageService.shared.updateItemById(synced)
                        print("[Delete] share 성공: contentId=\(result.id)")
                    } catch {
                        print("[Delete] share 실패: \(error.localizedDescription)")
                    }
                }
                if let contentId {
                    do {
                        try await BrieflyAPI.shared.swipe(contentId: contentId, action: .discard, token: token)
                        print("[Delete] swipe 성공: contentId=\(contentId)")
                    } catch {
                        print("[Delete] swipe 실패: \(error.localizedDescription)")
                    }
                } else {
                    print("[Delete] contentId 없음 — swipe 스킵")
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

    private func retryAISummary() {
        guard let contentId = currentItem.serverContentId,
              let token = AuthTokenStore.shared.accessToken else { return }

        StorageService.shared.updateSummaryStatus(for: currentItem.id, status: .unknown)

        Task {
            if let pageText = currentItem.articleText, pageText.count >= 200 {
                try? await BrieflyAPI.shared.rescan(
                    contentId: contentId, pageText: pageText, token: token, force: true
                )
                print("[Retry] rescan 전송: contentId=\(contentId), \(pageText.count)자")
            } else {
                print("[Retry] articleText 부족 — 폴링만 재시도: contentId=\(contentId)")
            }
        }

        isRetrying = true
        summaryPollId = UUID()
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
                Button("Discard") { performDelete() }
                    .frame(maxWidth: .infinity)
                    .foregroundStyle(Color.brieflyError)

                Divider().frame(height: 22)

                Button("Skip Now") { performSkip() }
                    .frame(maxWidth: .infinity)
                    .foregroundStyle(Color.brieflyInk400)

                Divider().frame(height: 22)

                Button("Keep") { performKeep() }
                    .frame(maxWidth: .infinity)
                    .foregroundStyle(Color.brieflyPrimary500)
            }
            .font(.subheadline.weight(.semibold))
            .padding(.vertical, 14)
            .background(Color.brieflyBgSurface)
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
                        .fill(Color.brieflyInk200)
                }
                .frame(width: 20, height: 20)
                .clipShape(RoundedRectangle(cornerRadius: 4))

                Text(currentItem.siteName?.uppercased() ?? currentItem.domain.uppercased())
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Color.brieflyInk400)
            }

            // 제목
            Text(currentItem.displayTitle)
                .font(.brieflyH1)
                .fixedSize(horizontal: false, vertical: true)

            // 저장 날짜
            Label(currentItem.savedAt.detailDateString, systemImage: "calendar")
                .font(.brieflyMeta)
                .foregroundStyle(Color.brieflyInk400)

            Divider()

            // AI 요약
            VStack(alignment: .leading, spacing: 10) {
                Label("AI 요약", systemImage: "sparkles")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Color.brieflyPrimary600)
                if let summary = loadedSummary ?? currentItem.summary {
                    Text(summary)
                        .font(.subheadline)
                        .foregroundStyle(Color.brieflyTextSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                } else if isSummaryLoading {
                    HStack(spacing: 8) {
                        ProgressView()
                            .scaleEffect(0.8)
                        Text("요약 생성 중...")
                            .font(.subheadline)
                            .foregroundStyle(Color.brieflyTextSecondary)
                    }
                } else {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("요약을 가져오지 못했습니다.")
                            .font(.subheadline)
                            .foregroundStyle(Color.brieflyTextSecondary)
                        Button(action: retryAISummary) {
                            Label("AI 요약 다시 시도", systemImage: "arrow.clockwise.circle")
                                .font(.subheadline.weight(.medium))
                                .foregroundStyle(Color.brieflyPrimary600)
                        }
                    }
                }
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.brieflyPrimary50, in: RoundedRectangle(cornerRadius: BrieflyRadius.md))
            .task(id: summaryPollId) {
                loadedSummary = nil
                let retrying = isRetrying
                isRetrying = false

                // summary 이미 있으면 즉시 종료 (버튼/스피너 모두 미표시)
                guard currentItem.summary == nil else { return }
                // serverContentId/토큰 없으면 즉시 종료 → isSummaryLoading 미설정 → 버튼 표시
                guard let contentId = currentItem.serverContentId,
                      let token = AuthTokenStore.shared.accessToken else { return }
                // 이전 세션 실패 항목은 재시도 버튼 탭 시에만 폴링
                guard currentItem.summaryStatus != .failed || retrying else { return }

                // 여기서부터 실제 폴링 시작
                isSummaryLoading = true
                defer { isSummaryLoading = false }  // 성공/실패/취소 모두 스피너 해제 → 버튼 표시

                for attempt in 0..<15 {
                    if attempt > 0 {
                        try? await Task.sleep(nanoseconds: 5_000_000_000)
                    }
                    if Task.isCancelled { return }
                    if let detail = try? await BrieflyAPI.shared.fetchContentDetail(contentId: contentId, token: token),
                       let summary = detail.summary {
                        loadedSummary = summary
                        StorageService.shared.updateSummary(for: currentItem.id, summary: summary)
                        StorageService.shared.updateSummaryStatus(for: currentItem.id, status: .done)
                        return
                    }
                }

                // 70초 타임아웃 — summaryStatus 저장 (다음 세션 자동 재폴링 방지)
                // UI 갱신은 defer의 isSummaryLoading = false 가 처리
                StorageService.shared.updateSummaryStatus(for: currentItem.id, status: .failed)
            }

            // 본문
            articleSection

            Divider()

            // 원문 보기
            Button { showBrowser = true } label: {
                HStack {
                    Image(systemName: "safari")
                    Text("원문 보기")
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.caption)
                        .foregroundStyle(Color.brieflyInk300)
                }
                .font(.body.weight(.medium))
                .foregroundStyle(Color.brieflyPrimary600)
                .padding(14)
                .background(Color.brieflyPrimary50, in: RoundedRectangle(cornerRadius: BrieflyRadius.md))
            }

            Text(currentItem.url.absoluteString)
                .font(.caption2)
                .foregroundStyle(Color.brieflyInk300)
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
                    .foregroundStyle(Color.brieflyTextSecondary)
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.brieflyInk50, in: RoundedRectangle(cornerRadius: BrieflyRadius.md))

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
                                .foregroundStyle(Color.brieflyPrimary500)
                        }
                    }
                    Text(text)
                        .font(.body)
                        .foregroundStyle(Color.brieflyTextPrimary)
                        .lineLimit(isArticleExpanded ? nil : 6)
                        .fixedSize(horizontal: false, vertical: true)
                        .animation(.easeInOut(duration: 0.2), value: isArticleExpanded)
                }
                .padding(14)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.brieflyInk50, in: RoundedRectangle(cornerRadius: BrieflyRadius.md))
            }
        }
    }

    private var faviconURL: URL? {
        URL(string: "https://www.google.com/s2/favicons?domain=\(currentItem.domain)&sz=64")
    }

    private var thumbnailPlaceholder: some View {
        Rectangle()
            .fill(Color.brieflyInk100)
            .overlay {
                Image(systemName: "photo")
                    .font(.system(size: 40))
                    .foregroundStyle(Color.brieflyInk300)
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

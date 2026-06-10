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
    @State private var isSummaryLoading = false
    @State private var loadedSummary: String? = nil
    @State private var liveItem: SavedItem? = nil
    @State private var summaryPollId = UUID()
    @State private var isRetrying = false
    @State private var diveDeeperQuestions: [String] = []
    @State private var isDiveDeeperLoading = false
    @State private var diveDeeperPollId = UUID()
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
            .gesture(swipeGesture)

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
        .onAppear {
            refreshLiveItem()
        }
        .onChange(of: currentIndex) { _ in
            summaryPollId = UUID()
            diveDeeperQuestions = []
            diveDeeperPollId = UUID()
            refreshLiveItem()
        }
        .onReceive(NotificationCenter.default.publisher(for: .fetchCoordinatorDidUpdate)) { _ in
            refreshLiveItem()
        }
        .task(id: summaryPollId) {
            loadedSummary = nil
            let retrying = isRetrying
            isRetrying = false

            let needsSummary = (loadedSummary ?? currentItem.summary) == nil
            let needsKeywords = currentItem.autoTagKeywordsEn.isEmpty
            guard needsSummary || needsKeywords else { return }
            guard let contentId = currentItem.serverContentId,
                  let token = AuthTokenStore.shared.accessToken else { return }
            guard currentItem.summaryStatus != .failed || retrying else { return }

            isSummaryLoading = needsSummary
            defer { isSummaryLoading = false }

            let deadline = Date().addingTimeInterval(90)
            for attempt in 0..<15 {
                if attempt > 0 {
                    try? await Task.sleep(nanoseconds: 5_000_000_000)
                }
                if Task.isCancelled { return }
                if Date() > deadline { break }
                if let detail = try? await BrieflyAPI.shared.fetchContentDetail(contentId: contentId, token: token) {
                    if !detail.autoTagKeywordsEn.isEmpty {
                        StorageService.shared.updateAutoTags(
                            for: currentItem.id,
                            category: detail.autoTagCategory,
                            keywordsEn: detail.autoTagKeywordsEn,
                            keywordsOriginal: detail.autoTagKeywordsOriginal
                        )
                        refreshLiveItem()
                    }
                    if let summary = detail.summary {
                        loadedSummary = summary
                        StorageService.shared.updateSummary(for: currentItem.id, summary: summary)
                        StorageService.shared.updateSummaryStatus(for: currentItem.id, status: .done)
                        return
                    }
                }
            }

            if (loadedSummary ?? currentItem.summary) == nil {
                StorageService.shared.updateSummaryStatus(for: currentItem.id, status: .failed)
            }
        }
        .task(id: diveDeeperPollId) {
            guard let contentId = currentItem.serverContentId,
                  let token = AuthTokenStore.shared.accessToken else { return }
            isDiveDeeperLoading = true
            defer { isDiveDeeperLoading = false }
            let questions = (try? await BrieflyAPI.shared.fetchDiveDeeperQuestions(
                contentId: contentId, token: token
            )) ?? []
            diveDeeperQuestions = questions
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
        isSummaryLoading = true  // 탭 즉시 스피너 표시 (token 확인 전에도)

        let itemId = currentItem.id
        let itemURL = currentItem.url
        // LinkedIn 구 저장 항목: articleText nil → ogTitle 폴백
        let isLinkedIn = itemURL.host?.lowercased().contains("linkedin.com") ?? false
        let cachedText = currentItem.articleText ?? (isLinkedIn ? currentItem.ogTitle : nil)

        Task {
            // 토큰 확보 — 없으면 refresh 시도
            let token: String
            if let t = AuthTokenStore.shared.accessToken {
                token = t
            } else if let t = await BrieflyAPI.shared.refreshCurrentToken() {
                token = t
            } else {
                isSummaryLoading = false
                return
            }

            StorageService.shared.updateSummaryStatus(for: itemId, status: .unknown)

            // 1. serverContentId 확보 (없으면 서버에 먼저 등록)
            var contentId = StorageService.shared.loadAll()
                .first(where: { $0.id == itemId })?.serverContentId
                ?? currentItem.serverContentId

            if contentId == nil {
                print("[Retry] serverContentId 없음 — share 먼저 시도: \(itemURL)")
                do {
                    let result = try await BrieflyAPI.shared.share(url: itemURL, token: token)
                    contentId = result.id
                    var synced = StorageService.shared.loadAll().first(where: { $0.id == itemId }) ?? currentItem
                    synced.serverContentId = result.id
                    StorageService.shared.updateItemById(synced)
                    liveItem = synced
                    print("[Retry] share 성공: contentId=\(result.id)")
                    if let summary = result.summary, !summary.isEmpty {
                        loadedSummary = summary
                        StorageService.shared.updateSummary(for: itemId, summary: summary)
                        StorageService.shared.updateSummaryStatus(for: itemId, status: .done)
                        isSummaryLoading = false
                        return
                    }
                } catch {
                    print("[Retry] share 실패: \(error.localizedDescription)")
                    isSummaryLoading = false
                    return
                }
            }

            guard let contentId else {
                isSummaryLoading = false
                return
            }

            // 2. pageText 결정: 캐시 부족하면 재크롤링
            var pageText = cachedText
            if (cachedText?.count ?? 0) < 200,
               !FetchCoordinator.isYouTubeURL(itemURL),
               !FetchCoordinator.isLinkedInURL(itemURL) {
                print("[Retry] articleText 부족 — 재크롤링 시도")
                let refetched = try? await FetchCoordinator.shared.fetchArticleText(for: itemURL)
                if let text = refetched {
                    pageText = text
                    var updated = StorageService.shared.loadAll().first(where: { $0.id == itemId }) ?? currentItem
                    updated.articleText = text
                    StorageService.shared.updateItemById(updated)
                }
            }

            // 3. rescan API 호출
            if let text = pageText, text.count >= 200 {
                try? await BrieflyAPI.shared.rescan(contentId: contentId, pageText: text, token: token, force: true)
                print("[Retry] rescan 전송: contentId=\(contentId), \(text.count)자")
            } else {
                print("[Retry] pageText 없음 — 폴링만 재시도: contentId=\(contentId)")
            }

            // 4. 폴링 재시작 (.task(id:)가 isSummaryLoading 제어 이어받음)
            isRetrying = true
            summaryPollId = UUID()
        }
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
                        .buttonStyle(.plain)
                    }
                }
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.brieflyPrimary50, in: RoundedRectangle(cornerRadius: BrieflyRadius.md))

            // Dive Deeper (IOS-015)
            if currentItem.serverContentId != nil && (isDiveDeeperLoading || !diveDeeperQuestions.isEmpty) {
                diveDeeperSection
            }

            // 키워드 / 카테고리
            if currentItem.autoTagCategory != nil || !currentItem.autoTagKeywordsEn.isEmpty {
                keywordsSection
            }

            // 본문
            articleSection

            Divider()

            // 원문 보기
            Button { UIApplication.shared.open(currentItem.url) } label: {
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

    private var keywordsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let category = currentItem.autoTagCategory {
                Text(category)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Color.brieflyPrimary600)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Color.brieflyPrimary50, in: Capsule())
                    .overlay(Capsule().stroke(Color.brieflyPrimary200, lineWidth: 1))
            }
            if !currentItem.autoTagKeywordsEn.isEmpty {
                KeywordPillRow(keywords: currentItem.autoTagKeywordsEn)
            }
        }
    }

    private var diveDeeperSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Label("Dive Deeper", systemImage: "lightbulb.fill")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Color.brieflyPrimary600)
                Text("더 깊이 생각해보기")
                    .font(.caption)
                    .foregroundStyle(Color.brieflyInk400)
            }

            if isDiveDeeperLoading {
                VStack(alignment: .leading, spacing: 10) {
                    ForEach(0..<3, id: \.self) { _ in
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.brieflyInk100)
                            .frame(maxWidth: .infinity)
                            .frame(height: 14)
                    }
                }
            } else {
                VStack(alignment: .leading, spacing: 10) {
                    ForEach(diveDeeperQuestions, id: \.self) { question in
                        HStack(alignment: .top, spacing: 8) {
                            Text("•")
                                .font(.subheadline.weight(.bold))
                                .foregroundStyle(Color.brieflyPrimary400)
                            Text(question)
                                .font(.subheadline)
                                .foregroundStyle(Color.brieflyTextSecondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.brieflyPrimary50, in: RoundedRectangle(cornerRadius: BrieflyRadius.md))
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
            // LinkedIn 구 저장 항목: articleText가 nil이어도 ogTitle에 본문이 담겨 있을 수 있음
            let isLinkedIn = currentItem.url.host?.lowercased().contains("linkedin.com") ?? false
            let bodyText = currentItem.articleText ?? (isLinkedIn ? currentItem.ogTitle : nil)
            if let text = bodyText, !text.isEmpty {
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
            } else if currentItem.fetchStatus == .partial {
                HStack(spacing: 8) {
                    Image(systemName: "doc.text")
                        .foregroundStyle(Color.brieflyInk300)
                    Text("본문을 직접 가져올 수 없습니다. 아래 원문에서 확인해 주세요.")
                        .font(.subheadline)
                        .foregroundStyle(Color.brieflyTextSecondary)
                }
                .padding(14)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.brieflyInk50, in: RoundedRectangle(cornerRadius: BrieflyRadius.md))
            }
        }
    }

    private func refreshLiveItem() {
        let baseItem = items[currentIndex]
        liveItem = StorageService.shared.loadAll().first(where: { $0.id == baseItem.id })
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

import SwiftUI

struct ItemDetailView: View {
    let item: SavedItem
    @State private var showBrowser = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {

                // ── 썸네일 (상단 풀너비) ──────────────────────────
                Group {
                    if let imageURL = item.ogImageURL {
                        AsyncImage(url: imageURL) { phase in
                            switch phase {
                            case .success(let image):
                                image.resizable().scaledToFill()
                            default:
                                thumbnailPlaceholder
                            }
                        }
                    } else {
                        thumbnailPlaceholder
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 220)
                .clipped()

                VStack(alignment: .leading, spacing: 20) {

                    // ── 출처 ──────────────────────────────────────
                    HStack(spacing: 8) {
                        AsyncImage(url: faviconURL) { image in
                            image.resizable().scaledToFill()
                        } placeholder: {
                            RoundedRectangle(cornerRadius: 4)
                                .fill(Color.secondary.opacity(0.25))
                        }
                        .frame(width: 20, height: 20)
                        .clipShape(RoundedRectangle(cornerRadius: 4))

                        Text(item.domain.uppercased())
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)
                    }

                    // ── 제목 ──────────────────────────────────────
                    Text(item.displayTitle)
                        .font(.title2.weight(.bold))
                        .fixedSize(horizontal: false, vertical: true)

                    // ── 저장 날짜 ─────────────────────────────────
                    Label(item.savedAt.detailDateString, systemImage: "calendar")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    Divider()

                    // ── AI 요약 ───────────────────────────────────
                    VStack(alignment: .leading, spacing: 10) {
                        Label("AI 요약", systemImage: "sparkles")
                            .font(.subheadline.weight(.semibold))

                        Text("AI 요약은 Phase 2에서 추가될 예정입니다.\nClaude API를 통해 본문 핵심 내용을 최대 300자로 요약해 드립니다.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(14)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.secondary.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))

                    Divider()

                    // ── 바로가기 버튼 ─────────────────────────────
                    Button {
                        showBrowser = true
                    } label: {
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

                    // ── URL 표시 ──────────────────────────────────
                    Text(item.url.absoluteString)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                        .lineLimit(2)
                }
                .padding(20)
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showBrowser) {
            SafariBrowserView(url: item.url)
        }
    }

    private var faviconURL: URL? {
        URL(string: "https://www.google.com/s2/favicons?domain=\(item.domain)&sz=64")
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
        ItemDetailView(item: SavedItem(
            url: URL(string: "https://linkedin.com/post/example")!,
            title: "Carnegie Mellon University School of Computer Science's Post"
        ))
    }
}

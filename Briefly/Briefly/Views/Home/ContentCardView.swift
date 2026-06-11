import SwiftUI

struct ContentCardView: View {
    let item: HomeItem
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: 0) {
                thumbnailView
                infoView
            }
        }
        .frame(width: 160)
        .background(Color.brieflyBgSurface)
        .clipShape(RoundedRectangle(cornerRadius: BrieflyRadius.md))
        .overlay(
            RoundedRectangle(cornerRadius: BrieflyRadius.md)
                .stroke(Color.brieflyBorder, lineWidth: 1)
        )
        .brieflyShadow1()
        .buttonStyle(.plain)
    }

    private var thumbnailView: some View {
        ZStack {
            Color.brieflyInk100
            if let url = item.thumbnailURL {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let img):
                        img.resizable().scaledToFill()
                    default:
                        domainInitial
                    }
                }
            } else {
                domainInitial
            }
        }
        .frame(height: 100)
        .clipped()
    }

    private var infoView: some View {
        VStack(alignment: .leading, spacing: BrieflySpacing.s1) {
            Text(item.displayTitle)
                .font(.brieflyBodySm)
                .foregroundStyle(Color.brieflyTextPrimary)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)

            Text("\(item.normalizedDomain) · \(item.savedAt.relativeShort)")
                .font(.brieflyCaption)
                .foregroundStyle(Color.brieflyInk400)
                .lineLimit(1)
        }
        .padding(BrieflySpacing.s2)
    }

    private var domainInitial: some View {
        Text(String(item.normalizedDomain.prefix(1)).uppercased())
            .font(.system(size: 28, weight: .semibold))
            .foregroundStyle(Color.brieflyInk300)
    }
}

private extension Date {
    var relativeShort: String {
        let f = RelativeDateTimeFormatter()
        f.locale = Locale(identifier: "ko_KR")
        f.unitsStyle = .abbreviated
        return f.localizedString(for: self, relativeTo: Date())
    }
}

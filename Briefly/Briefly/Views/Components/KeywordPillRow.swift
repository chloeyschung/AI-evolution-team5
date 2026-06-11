import SwiftUI

/// 웹 ContentCard의 `.tagRow` / `.keyword` CSS와 동일한 pill 행.
/// keywords가 빈 배열이면 EmptyView를 반환한다.
struct KeywordPillRow: View {
    let keywords: [String]
    var maxCount: Int = 8

    var body: some View {
        let visible = Array(keywords.prefix(maxCount))
        if visible.isEmpty {
            EmptyView()
        } else {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(visible, id: \.self) { kw in
                        Text(kw)
                            .font(.system(size: 11))
                            .foregroundStyle(Color.brieflyInk400)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(Color.brieflyInk50, in: Capsule())
                            .overlay(Capsule().stroke(Color.brieflyInk100, lineWidth: 1))
                    }
                }
                .padding(.horizontal, 1)
            }
        }
    }
}

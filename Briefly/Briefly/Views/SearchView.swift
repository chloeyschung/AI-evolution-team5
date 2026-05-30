import SwiftUI

struct SearchView: View {
    var body: some View {
        VStack(spacing: BrieflySpacing.s4) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 48))
                .foregroundStyle(Color.brieflyInk300)
            Text("Search")
                .font(.brieflyH2)
                .foregroundStyle(Color.brieflyTextPrimary)
            Text("준비 중입니다")
                .font(.brieflyBody)
                .foregroundStyle(Color.brieflyTextSecondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.brieflyBgApp.ignoresSafeArea())
        .navigationTitle("Search")
        .navigationBarTitleDisplayMode(.large)
    }
}

#Preview {
    NavigationStack { SearchView() }
}

import SwiftUI

struct SearchView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 60))
                .foregroundStyle(.secondary)
            Text("Search")
                .font(.headline)
            Text("준비 중입니다")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .navigationTitle("Search")
        .navigationBarTitleDisplayMode(.large)
    }
}

#Preview {
    NavigationStack { SearchView() }
}

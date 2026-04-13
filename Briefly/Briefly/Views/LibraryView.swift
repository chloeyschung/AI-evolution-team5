import SwiftUI

struct LibraryView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "books.vertical")
                .font(.system(size: 60))
                .foregroundStyle(.secondary)
            Text("Library")
                .font(.headline)
            Text("준비 중입니다")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .navigationTitle("Library")
        .navigationBarTitleDisplayMode(.large)
    }
}

#Preview {
    NavigationStack { LibraryView() }
}

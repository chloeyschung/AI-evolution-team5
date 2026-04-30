import SwiftUI

struct AccountView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "person.circle")
                .font(.system(size: 60))
                .foregroundStyle(.secondary)
            Text("Account")
                .font(.headline)
            Text("준비 중입니다")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .navigationTitle("Account")
        .navigationBarTitleDisplayMode(.large)
    }
}

#Preview {
    NavigationStack { AccountView() }
}

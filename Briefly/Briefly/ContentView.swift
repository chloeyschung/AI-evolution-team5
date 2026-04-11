import SwiftUI

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var viewModel = SavedItemsViewModel()

    var body: some View {
        NavigationStack {
            SavedItemsView(viewModel: viewModel)
        }
        .onChange(of: scenePhase) { newPhase in
            // 앱이 포그라운드로 올 때마다 inbox drain + 목록 갱신
            if newPhase == .active {
                viewModel.reload()
            }
        }
    }
}

#Preview {
    ContentView()
}

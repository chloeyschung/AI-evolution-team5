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
        .onOpenURL { url in
            // briefly://open?url=<articleURL> 처리
            viewModel.reload() // inbox drain
            guard
                url.scheme == "briefly",
                url.host == "open",
                let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
                let articleURLString = components.queryItems?.first(where: { $0.name == "url" })?.value,
                let articleURL = URL(string: articleURLString)
            else { return }
            UIApplication.shared.open(articleURL)
        }
    }
}

#Preview {
    ContentView()
}

import SwiftUI

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var viewModel = SavedItemsViewModel()
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {

            // MARK: Home
            NavigationStack {
                SavedItemsView(viewModel: viewModel)
            }
            .tabItem { Label("Home", systemImage: "house.fill") }
            .tag(0)

            // MARK: Library — NavigationStack은 LibraryView 내부에 있음
            LibraryView()
                .tabItem { Label("Library", systemImage: "books.vertical.fill") }
                .tag(1)

            // MARK: Search
            NavigationStack {
                SearchView()
            }
            .tabItem { Label("Search", systemImage: "magnifyingglass") }
            .tag(2)

            // MARK: Account
            NavigationStack {
                AccountView()
            }
            .tabItem { Label("Account", systemImage: "person.fill") }
            .tag(3)
        }
        .onChange(of: scenePhase) { newPhase in
            if newPhase == .active {
                viewModel.reload()
                Task {
                    await FetchCoordinator.shared.fetchIfNeeded(for: viewModel.items)
                }
            }
        }
        .onOpenURL { url in
            guard url.scheme == "briefly" else { return }

            if url.host == "item",
               let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
               let articleURLString = components.queryItems?.first(where: { $0.name == "url" })?.value,
               let articleURL = URL(string: articleURLString) {
                // Library 탭으로 전환 후 해당 아이템 상세 화면으로 이동
                viewModel.reload()
                selectedTab = 1
                NotificationCenter.default.post(name: .brieflyOpenItem, object: articleURL)
            }
        }
    }
}

#Preview {
    ContentView()
}

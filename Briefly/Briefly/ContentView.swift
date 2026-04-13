import SwiftUI

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var viewModel = SavedItemsViewModel()

    var body: some View {
        TabView {
            // MARK: Home
            NavigationStack {
                SavedItemsView(viewModel: viewModel)
            }
            .tabItem {
                Label("Home", systemImage: "house.fill")
            }

            // MARK: Library
            NavigationStack {
                LibraryView()
            }
            .tabItem {
                Label("Library", systemImage: "books.vertical.fill")
            }

            // MARK: Search
            NavigationStack {
                SearchView()
            }
            .tabItem {
                Label("Search", systemImage: "magnifyingglass")
            }

            // MARK: Account
            NavigationStack {
                AccountView()
            }
            .tabItem {
                Label("Account", systemImage: "person.fill")
            }
        }
        .onChange(of: scenePhase) { newPhase in
            if newPhase == .active {
                viewModel.reload()
            }
        }
        .onOpenURL { url in
            viewModel.reload()
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

import SwiftUI
import GoogleSignIn

@main
struct BrieflyApp: App {
    /// 이번 프로세스에서 스플래시를 이미 보여줬는지. Root view 재생성/scene 복원에도
    /// 한 번만 재생되도록 app(scene-graph) level state로 관리.
    @State private var didShowSplash = false

    init() {
        if let clientID = Bundle.main.object(forInfoDictionaryKey: "GIDClientID") as? String {
            GIDSignIn.sharedInstance.configuration = GIDConfiguration(clientID: clientID)
        }
    }

    var body: some Scene {
        WindowGroup {
            ZStack {
                ContentView()
                    .onOpenURL { url in
                        GIDSignIn.sharedInstance.handle(url)
                    }

                if !didShowSplash {
                    SplashView(onFinished: { didShowSplash = true })
                        .ignoresSafeArea()
                        .transition(.opacity)
                }
            }
        }
    }
}

import SwiftUI
import UIKit
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
        // UIScrollView의 기본 delaysTouchesBegan 동작이 ScrollView 내부 버튼 탭을 차단함.
        // false로 설정해 탭이 즉시 서브뷰에 전달되도록 함.
        UIScrollView.appearance().delaysContentTouches = false
    }

    var body: some Scene {
        WindowGroup {
            ZStack {
                ContentView()
                    .onOpenURL { url in
                        GIDSignIn.sharedInstance.handle(url)
                    }

                if !didShowSplash {
                    SplashView(onFinished: {
                        withAnimation(.easeOut(duration: 0.3)) { didShowSplash = true }
                    })
                        .ignoresSafeArea()
                        .transition(.opacity)
                }
            }
        }
    }
}

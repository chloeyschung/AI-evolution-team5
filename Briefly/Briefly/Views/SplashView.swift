import SwiftUI

struct SplashView: View {
    var onFinished: () -> Void

    @State private var logoOpacity: Double = 0
    @State private var logoOffset: CGFloat = 16
    @State private var screenOpacity: Double = 1

    var body: some View {
        ZStack {
            Color.brieflyBgApp.ignoresSafeArea()

            VStack(spacing: BrieflySpacing.s5) {
                Image("logo_full")
                    .renderingMode(.template)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 220)
                    .foregroundStyle(Color.brieflyPrimary600)

                Text("CONSUME. NOT COLLECT.")
                    .font(.brieflyMeta)
                    .foregroundStyle(Color.brieflyInk400)
                    .kerning(1.2)
            }
            .opacity(logoOpacity)
            .offset(y: logoOffset)
        }
        .opacity(screenOpacity)
        .task {
            // 등장 → 2초 유지 → 퇴장.
            // .task는 뷰 해제 시 자동 cancel되어 race condition 회피.
            withAnimation(.easeOut(duration: 0.45)) {
                logoOpacity = 1
                logoOffset  = 0
            }
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            withAnimation(.easeIn(duration: 0.35)) {
                screenOpacity = 0
            }
            try? await Task.sleep(nanoseconds: 350_000_000)
            onFinished()
        }
    }
}


#Preview {
    SplashView(onFinished: {})
}

import SwiftUI

struct SplashView: View {
    var onFinished: () -> Void

    @State private var logoOpacity: Double = 0
    @State private var logoOffset: CGFloat = 16
    @State private var screenOpacity: Double = 1

    var body: some View {
        ZStack {
            Color.brieflyBgApp.ignoresSafeArea()

            VStack(spacing: BrieflySpacing.s4) {
                BrieflyLogoMark(size: 96)

                Text("Briefly")
                    .font(.brieflyDisplay)
                    .foregroundStyle(Color.brieflyPrimary600)
                    .kerning(-0.5)

                Text("CONSUME. NOT COLLECT.")
                    .font(.brieflyMeta)
                    .foregroundStyle(Color.brieflyInk400)
                    .kerning(1.2)
                    .padding(.top, 2)
            }
            .opacity(logoOpacity)
            .offset(y: logoOffset)
        }
        .opacity(screenOpacity)
        .onAppear { animate() }
    }

    private func animate() {
        withAnimation(.easeOut(duration: 0.45)) {
            logoOpacity = 1
            logoOffset  = 0
        }
        // 2초 유지 후 퇴장
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            withAnimation(.easeIn(duration: 0.35)) {
                screenOpacity = 0
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                onFinished()
            }
        }
    }
}

// MARK: - 로고마크 (이미지 에셋 없이 SwiftUI로 직접 렌더링)

private struct BrieflyLogoMark: View {
    var size: CGFloat = 96

    var body: some View {
        ZStack {
            // 외곽 몸체
            RoundedRectangle(cornerRadius: size * 0.18, style: .continuous)
                .fill(Color.brieflyPrimary600)
                .frame(width: size, height: size * 0.84)

            // 두 개의 아치 창
            HStack(spacing: size * 0.07) {
                archWindow
                archWindow
            }
            .offset(y: size * 0.03)
        }
        .frame(width: size, height: size * 0.84)
    }

    private var archWindow: some View {
        let w = size * 0.33
        let h = size * 0.43

        return ZStack {
            // 아치 — 위는 반원, 아래는 직각
            UnevenRoundedRectangle(
                topLeadingRadius: w / 2,
                bottomLeadingRadius: 2,
                bottomTrailingRadius: 2,
                topTrailingRadius: w / 2
            )
            .fill(Color.brieflyBgApp)
            .frame(width: w, height: h)

            // 책 줄 — 아치 중간의 가로선
            Capsule()
                .fill(Color.brieflyPrimary300)
                .frame(width: w * 0.68, height: h * 0.08)
                .offset(y: h * 0.1)
        }
    }
}

#Preview {
    SplashView(onFinished: {})
}

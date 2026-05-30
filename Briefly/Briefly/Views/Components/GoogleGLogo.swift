import SwiftUI

/// 공식 Google G 로고를 Canvas로 렌더링.
///
/// SF Symbol `globe`이나 generic 아이콘 대신 브랜드 가이드라인을 따른 정확한 G 마크를 사용.
/// 좌표는 공식 SVG (viewBox 0 0 18 18)에서 추출.
struct GoogleGLogo: View {
    var size: CGFloat = 18

    var body: some View {
        Canvas { ctx, sz in
            let scale = sz.width / 18.0

            // Blue: top-right arc + right bar
            var p1 = Path()
            p1.move(to: CGPoint(x: 17.64 * scale, y: 9.2 * scale))
            p1.addCurve(
                to: CGPoint(x: 9 * scale, y: 7.36 * scale),
                control1: CGPoint(x: 17.58 * scale, y: 8.56 * scale),
                control2: CGPoint(x: 13.8 * scale, y: 7.36 * scale)
            )
            p1.addLine(to: CGPoint(x: 9 * scale, y: 10.84 * scale))
            p1.addLine(to: CGPoint(x: 13.84 * scale, y: 10.84 * scale))
            p1.addCurve(
                to: CGPoint(x: 12.05 * scale, y: 13.56 * scale),
                control1: CGPoint(x: 13.63 * scale, y: 11.97 * scale),
                control2: CGPoint(x: 13 * scale, y: 12.92 * scale)
            )
            p1.addLine(to: CGPoint(x: 14.96 * scale, y: 15.82 * scale))
            p1.addCurve(
                to: CGPoint(x: 17.64 * scale, y: 9.2 * scale),
                control1: CGPoint(x: 16.66 * scale, y: 14.25 * scale),
                control2: CGPoint(x: 17.64 * scale, y: 11.96 * scale)
            )
            p1.closeSubpath()
            ctx.fill(p1, with: .color(Color(red: 0.259, green: 0.522, blue: 0.957)))

            // Green: bottom-right
            var p2 = Path()
            p2.move(to: CGPoint(x: 9 * scale, y: 18 * scale))
            p2.addCurve(
                to: CGPoint(x: 14.96 * scale, y: 15.82 * scale),
                control1: CGPoint(x: 11.43 * scale, y: 18 * scale),
                control2: CGPoint(x: 13.47 * scale, y: 17.19 * scale)
            )
            p2.addLine(to: CGPoint(x: 12.05 * scale, y: 13.56 * scale))
            p2.addCurve(
                to: CGPoint(x: 9 * scale, y: 14.42 * scale),
                control1: CGPoint(x: 11.24 * scale, y: 14.1 * scale),
                control2: CGPoint(x: 10.21 * scale, y: 14.42 * scale)
            )
            p2.addCurve(
                to: CGPoint(x: 3.96 * scale, y: 10.71 * scale),
                control1: CGPoint(x: 6.66 * scale, y: 14.42 * scale),
                control2: CGPoint(x: 4.67 * scale, y: 12.83 * scale)
            )
            p2.addLine(to: CGPoint(x: 0.96 * scale, y: 13.04 * scale))
            p2.addCurve(
                to: CGPoint(x: 9 * scale, y: 18 * scale),
                control1: CGPoint(x: 2.93 * scale, y: 15.88 * scale),
                control2: CGPoint(x: 5.72 * scale, y: 18 * scale)
            )
            p2.closeSubpath()
            ctx.fill(p2, with: .color(Color(red: 0.204, green: 0.659, blue: 0.325)))

            // Yellow: bottom-left
            var p3 = Path()
            p3.move(to: CGPoint(x: 3.96 * scale, y: 10.71 * scale))
            p3.addCurve(
                to: CGPoint(x: 3.68 * scale, y: 9 * scale),
                control1: CGPoint(x: 3.79 * scale, y: 10.16 * scale),
                control2: CGPoint(x: 3.68 * scale, y: 9.59 * scale)
            )
            p3.addCurve(
                to: CGPoint(x: 3.96 * scale, y: 7.29 * scale),
                control1: CGPoint(x: 3.68 * scale, y: 8.41 * scale),
                control2: CGPoint(x: 3.79 * scale, y: 7.83 * scale)
            )
            p3.addLine(to: CGPoint(x: 0.96 * scale, y: 4.96 * scale))
            p3.addCurve(
                to: CGPoint(x: 0 * scale, y: 9 * scale),
                control1: CGPoint(x: 0.35 * scale, y: 6.12 * scale),
                control2: CGPoint(x: 0 * scale, y: 7.51 * scale)
            )
            p3.addCurve(
                to: CGPoint(x: 0.96 * scale, y: 13.04 * scale),
                control1: CGPoint(x: 0 * scale, y: 10.49 * scale),
                control2: CGPoint(x: 0.35 * scale, y: 11.88 * scale)
            )
            p3.addLine(to: CGPoint(x: 3.96 * scale, y: 10.71 * scale))
            p3.closeSubpath()
            ctx.fill(p3, with: .color(Color(red: 0.984, green: 0.737, blue: 0.020)))

            // Red: top-left
            var p4 = Path()
            p4.move(to: CGPoint(x: 9 * scale, y: 3.58 * scale))
            p4.addCurve(
                to: CGPoint(x: 12.44 * scale, y: 4.93 * scale),
                control1: CGPoint(x: 10.32 * scale, y: 3.58 * scale),
                control2: CGPoint(x: 11.51 * scale, y: 4.03 * scale)
            )
            p4.addLine(to: CGPoint(x: 15.02 * scale, y: 2.35 * scale))
            p4.addCurve(
                to: CGPoint(x: 9 * scale, y: 0 * scale),
                control1: CGPoint(x: 13.46 * scale, y: 0.89 * scale),
                control2: CGPoint(x: 11.43 * scale, y: 0 * scale)
            )
            p4.addCurve(
                to: CGPoint(x: 0.96 * scale, y: 4.96 * scale),
                control1: CGPoint(x: 5.72 * scale, y: 0 * scale),
                control2: CGPoint(x: 2.93 * scale, y: 2.12 * scale)
            )
            p4.addLine(to: CGPoint(x: 3.96 * scale, y: 7.29 * scale))
            p4.addCurve(
                to: CGPoint(x: 9 * scale, y: 3.58 * scale),
                control1: CGPoint(x: 4.67 * scale, y: 5.17 * scale),
                control2: CGPoint(x: 6.66 * scale, y: 3.58 * scale)
            )
            p4.closeSubpath()
            ctx.fill(p4, with: .color(Color(red: 0.918, green: 0.263, blue: 0.208)))
        }
        .frame(width: size, height: size)
    }
}

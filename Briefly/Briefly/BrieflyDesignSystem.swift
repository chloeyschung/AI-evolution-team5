import SwiftUI

// MARK: - Color Tokens
// Reference: docs/design.md (single source of truth for design tokens)

extension Color {
    // Primary — Olive Forest
    static let brieflyPrimary50  = Color(hex: 0xF0F2EA)
    static let brieflyPrimary100 = Color(hex: 0xDDE0CE)
    static let brieflyPrimary200 = Color(hex: 0xB8BFA1)
    static let brieflyPrimary300 = Color(hex: 0x929977)
    static let brieflyPrimary400 = Color(hex: 0x6E7654) // 링크 hover
    static let brieflyPrimary500 = Color(hex: 0x4F5938) // Primary 액션 기본 (Keep)
    static let brieflyPrimary600 = Color(hex: 0x3A4229) // 로고 / 브랜드
    static let brieflyPrimary700 = Color(hex: 0x2B311E) // Pressed
    static let brieflyPrimary800 = Color(hex: 0x1F2415) // Dark mode surface
    static let brieflyPrimary900 = Color(hex: 0x15180D) // Dark mode deep surface

    // Paper — Warm Off-white
    static let brieflyPaper50  = Color(hex: 0xFAFAF8) // 앱 기본 배경 (라이트)
    static let brieflyPaper100 = Color(hex: 0xFFFFFF) // 카드 표면
    static let brieflyPaper200 = Color(hex: 0xF2F2EE) // 디바이더
    static let brieflyPaper300 = Color(hex: 0xE5E5DE) // 보더
    static let brieflyPaper400 = Color(hex: 0xC7C7BD) // 비활성 텍스트 위

    // Accent — Sunrise (성취 / Gain / 스트릭)
    static let brieflyAccent50  = Color(hex: 0xFDF4E8)
    static let brieflyAccent100 = Color(hex: 0xFBE6CB)
    static let brieflyAccent300 = Color(hex: 0xF2BE85)
    static let brieflyAccent500 = Color(hex: 0xE89B5C) // 성취 강조 (Cleared, streak)
    static let brieflyAccent700 = Color(hex: 0xB26F3A)
    static let brieflyAccent900 = Color(hex: 0x7A4920)

    // Ink — Text / Border
    static let brieflyInk50  = Color(hex: 0xF5F6F0) // 미묘한 표면
    static let brieflyInk100 = Color(hex: 0xEAECE3) // 디바이더
    static let brieflyInk200 = Color(hex: 0xD7DAD0) // 보더
    static let brieflyInk300 = Color(hex: 0xB8BCB0) // 비활성 텍스트
    static let brieflyInk400 = Color(hex: 0x909488) // 메타데이터
    static let brieflyInk500 = Color(hex: 0x71756A) // 보조 텍스트
    static let brieflyInk700 = Color(hex: 0x3D4135) // 본문 텍스트
    static let brieflyInk900 = Color(hex: 0x1A1D14) // 제목 텍스트

    // Semantic
    static let brieflySuccess = Color.brieflyPrimary500              // Primary-500 재사용 (일관성)
    static let brieflyInfo    = Color(hex: 0x5A7AA8)                 // 차분한 슬레이트 블루
    static let brieflyWarning = Color(hex: 0xD89A3A)                 // Sunrise 차용
    static let brieflyError   = Color(hex: 0xB65A4E)                 // 테라코타 (Guilt-Free, 공격적 빨강 금지)

    // Aliases (semantic roles)
    static let brieflyBrand          = Color.brieflyPrimary600
    static let brieflyBgApp          = Color.brieflyPaper50
    static let brieflyBgSurface      = Color.brieflyPaper100
    static let brieflyBgElevated     = Color.brieflyPaper100
    static let brieflyTextPrimary    = Color.brieflyInk900
    static let brieflyTextSecondary  = Color.brieflyInk500
    static let brieflyBorder         = Color.brieflyPaper300

    init(hex: UInt32) {
        let r = Double((hex >> 16) & 0xFF) / 255
        let g = Double((hex >> 8) & 0xFF) / 255
        let b = Double(hex & 0xFF) / 255
        self.init(red: r, green: g, blue: b)
    }
}

// MARK: - Spacing

enum BrieflySpacing {
    static let s0:  CGFloat = 0
    static let s1:  CGFloat = 4
    static let s2:  CGFloat = 8
    static let s3:  CGFloat = 12
    static let s4:  CGFloat = 16   // 카드 본문 내부 기본
    static let s5:  CGFloat = 20
    static let s6:  CGFloat = 24   // 카드 외곽 padding, 화면 좌우 margin (모바일)
    static let s8:  CGFloat = 32
    static let s10: CGFloat = 40
    static let s12: CGFloat = 48
    static let s16: CGFloat = 64
}

// MARK: - Radius

enum BrieflyRadius {
    static let xs:   CGFloat = 4
    static let sm:   CGFloat = 8
    static let md:   CGFloat = 12
    static let lg:   CGFloat = 16
    static let xl:   CGFloat = 24
    static let full: CGFloat = 9999 // 아바타, 토글, pill
}

// MARK: - Motion (Durations in seconds)

enum BrieflyMotion {
    static let instant: Double = 0.08 // 색상 변경, focus ring
    static let fast:    Double = 0.16 // hover, 작은 transform
    static let base:    Double = 0.24 // 카드 전환 기본
    static let slow:    Double = 0.32 // 카드 퇴장 / 큰 transform
    static let page:    Double = 0.40 // 페이지 / 시트 전환
}

// MARK: - Typography
// 커스텀 폰트(Instrument Serif, IBM Plex Sans, Pretendard) 추가 전까지 시스템 폰트 사용.
// 추가 후 각 static var의 .system(...) 을 커스텀 폰트로 교체.

extension Font {
    static var brieflyDisplay: Font { .system(size: 40, weight: .regular, design: .serif) }
    static var brieflyH1:      Font { .system(size: 28, weight: .medium,  design: .serif) }
    static var brieflyH2:      Font { .system(size: 22, weight: .semibold) }
    static var brieflyH3:      Font { .system(size: 18, weight: .semibold) }
    static var brieflyH4:      Font { .system(size: 16, weight: .semibold) }
    static var brieflyBody:    Font { .system(size: 15, weight: .regular) }
    static var brieflyBodySm:  Font { .system(size: 13, weight: .regular) }
    static var brieflyLabel:   Font { .system(size: 12, weight: .medium) }
    static var brieflyMeta:    Font { .system(size: 11, weight: .regular, design: .monospaced) }
    static var brieflyCaption: Font { .system(size: 11, weight: .regular) }
}

// MARK: - Shadow

extension View {
    func brieflyShadow1() -> some View {
        self.shadow(color: Color.brieflyInk900.opacity(0.04), radius: 2, x: 0, y: 1)
            .shadow(color: Color.brieflyInk900.opacity(0.03), radius: 1, x: 0, y: 1)
    }

    func brieflyShadow2() -> some View {
        self.shadow(color: Color.brieflyInk900.opacity(0.06), radius: 6, x: 0, y: 2)
            .shadow(color: Color.brieflyInk900.opacity(0.04), radius: 2, x: 0, y: 1)
    }

    func brieflyShadow3() -> some View {
        self.shadow(color: Color.brieflyInk900.opacity(0.08), radius: 20, x: 0, y: 8)
            .shadow(color: Color.brieflyInk900.opacity(0.05), radius: 6, x: 0, y: 2)
    }

    func brieflyShadow4() -> some View {
        self.shadow(color: Color.brieflyInk900.opacity(0.12), radius: 40, x: 0, y: 20)
    }
}

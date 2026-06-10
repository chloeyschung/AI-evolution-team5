import Foundation

enum HomeDateBucket: String, CaseIterable {
    case today     = "오늘 저장한 따끈따끈한 글"
    case thisWeek  = "이번주에 발견한 좋은 글"
    case lastWeek  = "놓치지 마세요! 지난주에 담아둔"
    case thisMonth = "이번 달의 링크들"
    case lastMonth = "한달전의 내가 저장한 글"
    case older     = "오랜만에 꺼내 읽어 볼까요?"

    static func bucket(for date: Date, relativeTo now: Date = Date()) -> HomeDateBucket {
        let cal = Calendar.current
        let startOfToday = cal.startOfDay(for: now)

        if date >= startOfToday { return .today }

        // 월요일 00:00 기준 (weekday: 1=일, 2=월 ... 7=토)
        let weekday = cal.component(.weekday, from: now)
        let daysSinceMonday = (weekday + 5) % 7
        let startOfWeek = cal.date(byAdding: .day, value: -daysSinceMonday, to: startOfToday)!
        if date >= startOfWeek { return .thisWeek }

        let startOfLastWeek = cal.date(byAdding: .day, value: -7, to: startOfWeek)!
        if date >= startOfLastWeek { return .lastWeek }

        let startOfMonth = cal.date(from: cal.dateComponents([.year, .month], from: now))!
        if date >= startOfMonth { return .thisMonth }

        let startOfLastMonth = cal.date(byAdding: .month, value: -1, to: startOfMonth)!
        if date >= startOfLastMonth { return .lastMonth }

        return .older
    }
}

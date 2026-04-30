import Foundation

/// App Group UserDefaults를 통해 인증 토큰을 저장합니다 (메인 앱 ↔ Share Extension 공유).
///
/// Target Membership: Briefly + BrieflyShareExtension 양쪽 모두 추가 필요.
final class AuthTokenStore {
    static let shared = AuthTokenStore()

    private let appGroupID = "group.com.briefly.shared"
    private let accessTokenKey = "briefly.auth.access_token"
    private let refreshTokenKey = "briefly.auth.refresh_token"
    private let userIdKey = "briefly.auth.user_id"
    private let displayNameKey = "briefly.auth.display_name"
    private let emailKey = "briefly.auth.email"

    private var defaults: UserDefaults? {
        UserDefaults(suiteName: appGroupID)
    }

    private init() {}

    var accessToken: String? {
        get { defaults?.string(forKey: accessTokenKey) }
        set { defaults?.set(newValue, forKey: accessTokenKey) }
    }

    var refreshToken: String? {
        get { defaults?.string(forKey: refreshTokenKey) }
        set { defaults?.set(newValue, forKey: refreshTokenKey) }
    }

    var userId: Int? {
        get {
            let val = defaults?.integer(forKey: userIdKey) ?? 0
            return val == 0 ? nil : val
        }
        set { defaults?.set(newValue, forKey: userIdKey) }
    }

    var displayName: String? {
        get { defaults?.string(forKey: displayNameKey) }
        set { defaults?.set(newValue, forKey: displayNameKey) }
    }

    var email: String? {
        get { defaults?.string(forKey: emailKey) }
        set { defaults?.set(newValue, forKey: emailKey) }
    }

    var isLoggedIn: Bool { accessToken != nil }

    func save(accessToken: String, refreshToken: String, userId: Int, displayName: String?, email: String?) {
        self.accessToken = accessToken
        self.refreshToken = refreshToken
        self.userId = userId
        self.displayName = displayName
        self.email = email
    }

    func clear() {
        defaults?.removeObject(forKey: accessTokenKey)
        defaults?.removeObject(forKey: refreshTokenKey)
        defaults?.removeObject(forKey: userIdKey)
        defaults?.removeObject(forKey: displayNameKey)
        defaults?.removeObject(forKey: emailKey)
    }
}

import Foundation

/// Briefly 백엔드 API 클라이언트.
///
/// Target Membership: Briefly + BrieflyShareExtension 양쪽 모두 추가 필요.
actor BrieflyAPI {
    static let shared = BrieflyAPI()

    private let baseURL: URL
    private let session: URLSession

    private init() {
        #if DEBUG
        baseURL = URL(string: "http://localhost:8000/api/v1")!
        #else
        baseURL = URL(string: "https://api.briefly.app/api/v1")!
        #endif

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        session = URLSession(configuration: config)
    }

    // MARK: - Share

    struct SharePayload: Encodable {
        let content: String
        let platform: String
    }

    struct ShareResult: Decodable {
        let id: Int
        let url: String
        let title: String?
        let platform: String
        let createdAt: String

        enum CodingKeys: String, CodingKey {
            case id, url, title, platform
            case createdAt = "created_at"
        }
    }

    func share(url: URL, token: String) async throws -> ShareResult {
        let body = SharePayload(content: url.absoluteString, platform: url.host ?? "web")
        return try await post("/share", body: body, token: token)
    }

    // MARK: - Auth: Email / Password

    struct EmailLoginPayload: Encodable {
        let email: String
        let password: String
    }

    struct EmailLoginResult: Decodable {
        let accessToken: String
        let refreshToken: String
        let expiresAt: String
        let userId: Int
        let email: String

        enum CodingKeys: String, CodingKey {
            case accessToken = "access_token"
            case refreshToken = "refresh_token"
            case expiresAt = "expires_at"
            case userId = "user_id"
            case email
        }
    }

    func loginWithEmail(email: String, password: String) async throws -> EmailLoginResult {
        let body = EmailLoginPayload(email: email, password: password)
        return try await post("/auth/login", body: body, token: nil)
    }

    // MARK: - Auth: Google

    struct GoogleUserInfoPayload: Encodable {
        let id: String
        let email: String
        let name: String?
        let picture: String?
    }

    struct GoogleLoginPayload: Encodable {
        let googleIdToken: String
        let googleUserInfo: GoogleUserInfoPayload

        enum CodingKeys: String, CodingKey {
            case googleIdToken = "google_id_token"
            case googleUserInfo = "google_user_info"
        }
    }

    struct GoogleLoginResult: Decodable {
        let accessToken: String
        let refreshToken: String
        let expiresAt: String
        let user: GoogleUser
        let isNewUser: Bool

        struct GoogleUser: Decodable {
            let id: Int
            let email: String
            let displayName: String?
            let avatarUrl: String?

            enum CodingKeys: String, CodingKey {
                case id, email
                case displayName = "display_name"
                case avatarUrl = "avatar_url"
            }
        }

        enum CodingKeys: String, CodingKey {
            case accessToken = "access_token"
            case refreshToken = "refresh_token"
            case expiresAt = "expires_at"
            case user
            case isNewUser = "is_new_user"
        }
    }

    func loginWithGoogle(
        idToken: String,
        userID: String,
        email: String,
        name: String?,
        picture: String?
    ) async throws -> GoogleLoginResult {
        let userInfo = GoogleUserInfoPayload(id: userID, email: email, name: name, picture: picture)
        let body = GoogleLoginPayload(googleIdToken: idToken, googleUserInfo: userInfo)
        return try await post("/auth/google", body: body, token: nil)
    }

    // MARK: - Auth: Refresh

    struct RefreshPayload: Encodable {
        let refreshToken: String

        enum CodingKeys: String, CodingKey {
            case refreshToken = "refresh_token"
        }
    }

    struct RefreshResult: Decodable {
        let accessToken: String
        let refreshToken: String
        let expiresAt: String

        enum CodingKeys: String, CodingKey {
            case accessToken = "access_token"
            case refreshToken = "refresh_token"
            case expiresAt = "expires_at"
        }
    }

    func refreshToken(refreshToken: String) async throws -> RefreshResult {
        let body = RefreshPayload(refreshToken: refreshToken)
        return try await post("/auth/refresh", body: body, token: nil)
    }

    // MARK: - Device Token

    struct DeviceTokenPayload: Encodable {
        let deviceToken: String
        let platform: String

        enum CodingKeys: String, CodingKey {
            case deviceToken = "device_token"
            case platform
        }
    }

    func registerDeviceToken(_ token: String, authToken: String) async throws {
        let body = DeviceTokenPayload(deviceToken: token, platform: "ios")
        let _: EmptyResponse = try await post("/user/device-token", body: body, token: authToken)
    }

    // MARK: - HTTP helpers

    private struct EmptyResponse: Decodable {}

    enum APIError: LocalizedError {
        case httpError(Int, String?)
        case noToken

        var errorDescription: String? {
            switch self {
            case .httpError(let code, let message):
                return message ?? "서버 오류 (\(code))"
            case .noToken:
                return "로그인이 필요합니다"
            }
        }
    }

    private func post<B: Encodable, R: Decodable>(_ path: String, body: B, token: String?) async throws -> R {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.httpError(0, nil)
        }
        guard (200...299).contains(http.statusCode) else {
            let message = (try? JSONDecoder().decode([String: String].self, from: data))?["message"]
            throw APIError.httpError(http.statusCode, message)
        }
        return try JSONDecoder().decode(R.self, from: data)
    }
}

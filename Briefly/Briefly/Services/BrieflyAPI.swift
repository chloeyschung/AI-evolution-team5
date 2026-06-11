import Foundation

/// Briefly 백엔드 API 클라이언트.
///
/// Target Membership: Briefly + BrieflyShareExtension 양쪽 모두 추가 필요.
actor BrieflyAPI {
    static let shared = BrieflyAPI()

    private var baseURL: URL
    private let session: URLSession

    static let devURLKey = "briefly_dev_base_url"
    static let defaultDevURL = "https://briefly-api-production-2a40.up.railway.app/api/v1"

    /// 환경별 기본 baseURL. Simulator는 localhost, 실기기 DEBUG는 Railway, Release는 prod.
    /// DevServerSheet와 init이 같은 값을 보도록 single source.
    static var defaultDebugURL: String {
        #if targetEnvironment(simulator)
        return "http://127.0.0.1:8000/api/v1"
        #else
        return defaultDevURL
        #endif
    }

    private init() {
        #if DEBUG
        let stored = UserDefaults.standard.string(forKey: BrieflyAPI.devURLKey) ?? ""
        let urlString = stored.isEmpty ? BrieflyAPI.defaultDebugURL : stored
        baseURL = URL(string: urlString) ?? URL(string: BrieflyAPI.defaultDebugURL)!
        print("[BrieflyAPI] baseURL: \(baseURL)")
        #else
        baseURL = URL(string: "https://api.briefly.app/api/v1")!
        #endif

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        session = URLSession(configuration: config)
    }

    /// DevServerSheet 등에서 호출하는 URL 검증.
    /// scheme/host 필수, `/api/v1` 경로 필수.
    static func validateBaseURLString(_ urlString: String) -> URL? {
        let trimmed = urlString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let comps = URLComponents(string: trimmed),
              let scheme = comps.scheme?.lowercased(),
              (scheme == "http" || scheme == "https"),
              let host = comps.host, !host.isEmpty else {
            return nil
        }
        // 백엔드 라우터가 /api/v1 prefix이므로 경로 필수.
        let normalizedPath = comps.path.trimmingCharacters(in: .init(charactersIn: "/"))
        guard normalizedPath.contains("api/v1") else { return nil }
        return comps.url
    }

    /// 유효한 dev URL이면 적용 + 저장, 아니면 false 반환.
    @discardableResult
    func updateBaseURL(_ urlString: String) -> Bool {
        guard let url = BrieflyAPI.validateBaseURLString(urlString) else { return false }
        baseURL = url
        UserDefaults.standard.set(url.absoluteString, forKey: BrieflyAPI.devURLKey)
        return true
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
        let summary: String?

        enum CodingKeys: String, CodingKey {
            case id, url, title, platform, summary
            case createdAt = "created_at"
        }
    }

    func share(url: URL, token: String) async throws -> ShareResult {
        let body = SharePayload(content: url.absoluteString, platform: url.host ?? "web")
        return try await post("/share", body: body, token: token)
    }

    // MARK: - Rescan (page_text 기반 재요약 트리거)

    struct RescanPayload: Encodable {
        let pageText: String
        let force: Bool

        enum CodingKeys: String, CodingKey {
            case pageText = "page_text"
            case force
        }
    }

    private struct RescanResult: Decodable {
        let status: String
    }

    func rescan(contentId: Int, pageText: String, token: String, force: Bool = false) async throws {
        let body = RescanPayload(pageText: pageText, force: force)
        let _: RescanResult = try await post("/content/\(contentId)/rescan", body: body, token: token)
    }

    // MARK: - Content Detail

    struct ContentDetail: Decodable {
        let id: Int
        let summary: String?
        let autoTagCategory: String?
        let autoTagKeywordsEn: [String]
        let autoTagKeywordsOriginal: [String]

        enum CodingKeys: String, CodingKey {
            case id, summary
            case autoTagCategory      = "auto_tag_category"
            case autoTagKeywordsEn    = "auto_tag_keywords_en"
            case autoTagKeywordsOriginal = "auto_tag_keywords_original"
        }

        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            id      = try  c.decode(Int.self,    forKey: .id)
            summary = try? c.decode(String.self, forKey: .summary)
            autoTagCategory         = try? c.decode(String.self,   forKey: .autoTagCategory)
            autoTagKeywordsEn       = (try? c.decode([String].self, forKey: .autoTagKeywordsEn))       ?? []
            autoTagKeywordsOriginal = (try? c.decode([String].self, forKey: .autoTagKeywordsOriginal)) ?? []
        }
    }

    func fetchContentDetail(contentId: Int, token: String) async throws -> ContentDetail {
        return try await get("/content/\(contentId)", token: token)
    }

    // MARK: - Content List (IOS-006)

    private struct PaginatedContentResponse: Decodable {
        let items: [ServerContent]
        let total: Int
        let hasMore: Bool
        let nextOffset: Int?

        enum CodingKeys: String, CodingKey {
            case items, total
            case hasMore     = "has_more"
            case nextOffset  = "next_offset"
        }
    }

    func fetchServerContent(token: String, limit: Int = 200) async throws -> [ServerContent] {
        let response: PaginatedContentResponse = try await get(
            "/content",
            token: token,
            queryItems: [URLQueryItem(name: "limit", value: "\(limit)")]
        )
        return response.items
    }

    // MARK: - Topic Clusters (IOS-008)

    private struct TopicClustersResponse: Decodable {
        let clusters: [TopicCluster]
    }

    func fetchTopicClusters(token: String) async throws -> [TopicCluster] {
        let response: TopicClustersResponse = try await get("/topics", token: token)
        return response.clusters
    }

    // MARK: - Dive Deeper (IOS-015)

    private struct DiveDeeperResponse: Decodable {
        let contentId: Int
        let questions: [String]

        enum CodingKeys: String, CodingKey {
            case contentId = "content_id"
            case questions
        }
    }

    func fetchDiveDeeperQuestions(contentId: Int, token: String) async throws -> [String] {
        let langCode = Locale.current.language.languageCode?.identifier ?? "en"
        let response: DiveDeeperResponse = try await get(
            "/content/\(contentId)/reflection-questions",
            token: token,
            queryItems: [URLQueryItem(name: "lang", value: langCode)]
        )
        return response.questions
    }

    // MARK: - GET helper

    private func get<R: Decodable>(
        _ path: String,
        token: String,
        queryItems: [URLQueryItem] = []
    ) async throws -> R {
        var url = baseURL.appendingPathComponent(path)
        if !queryItems.isEmpty,
           var comps = URLComponents(url: url, resolvingAgainstBaseURL: false) {
            comps.queryItems = queryItems
            url = comps.url ?? url
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.httpError(0, nil)
        }
        guard (200...299).contains(http.statusCode) else {
            throw APIError.httpError(http.statusCode, BrieflyAPI.decodeErrorMessage(from: data))
        }
        return try JSONDecoder().decode(R.self, from: data)
    }

    // MARK: - Swipe (Keep / Discard)

    enum SwipeAction: String, Encodable {
        case keep
        case discard
    }

    struct SwipePayload: Encodable {
        let contentId: Int
        let action: SwipeAction

        enum CodingKeys: String, CodingKey {
            case contentId = "content_id"
            case action
        }
    }

    struct SwipeResult: Decodable {
        let id: Int
        let contentId: Int
        let action: String

        enum CodingKeys: String, CodingKey {
            case id
            case contentId = "content_id"
            case action
        }
    }

    func swipe(contentId: Int, action: SwipeAction, token: String) async throws -> SwipeResult {
        let body = SwipePayload(contentId: contentId, action: action)
        return try await post("/swipe", body: body, token: token)
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

    /// 저장된 refreshToken으로 accessToken을 갱신하고 AuthTokenStore에 저장합니다.
    /// 성공하면 새 accessToken을 반환, 실패하면 nil을 반환합니다.
    func refreshCurrentToken() async -> String? {
        guard let rt = AuthTokenStore.shared.refreshToken else {
            print("[BrieflyAPI] refreshToken 없음 — 재로그인 필요")
            return nil
        }
        do {
            let result = try await refreshToken(refreshToken: rt)
            AuthTokenStore.shared.accessToken = result.accessToken
            AuthTokenStore.shared.refreshToken = result.refreshToken
            print("[BrieflyAPI] 토큰 갱신 성공")
            return result.accessToken
        } catch {
            print("[BrieflyAPI] 토큰 갱신 실패: \(error.localizedDescription)")
            return nil
        }
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

    /// 백엔드 표준 에러 응답을 통일된 메시지로 디코드.
    /// 우선순위: `message` (POST 표준) → `detail` (FastAPI/일부 GET) → `error` (custom)
    private static func decodeErrorMessage(from data: Data) -> String? {
        if let dict = try? JSONDecoder().decode([String: String].self, from: data) {
            return dict["message"] ?? dict["detail"] ?? dict["error"]
        }
        return nil
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
            throw APIError.httpError(http.statusCode, BrieflyAPI.decodeErrorMessage(from: data))
        }
        return try JSONDecoder().decode(R.self, from: data)
    }
}

import SwiftUI
import GoogleSignIn

struct AccountView: View {
    @StateObject private var viewModel = AuthViewModel()
    @State private var showDevSettings = false

    var body: some View {
        Group {
            if viewModel.isLoggedIn {
                loggedInView
            } else {
                loginView
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.brieflyBgApp.ignoresSafeArea())
        .navigationTitle("Account")
        .navigationBarTitleDisplayMode(.large)
        #if DEBUG
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button { showDevSettings = true } label: {
                    Image(systemName: "antenna.radiowaves.left.and.right")
                        .foregroundStyle(Color.brieflyInk400)
                }
            }
        }
        .sheet(isPresented: $showDevSettings) {
            DevServerSheet()
        }
        #endif
        .alert("오류", isPresented: $viewModel.showError) {
            Button("확인") {}
        } message: {
            Text(viewModel.errorMessage ?? "알 수 없는 오류가 발생했습니다")
        }
    }

    // MARK: - 로그인 상태

    private var loggedInView: some View {
        VStack(spacing: 20) {
            Image(systemName: "person.circle.fill")
                .font(.system(size: 64))
                .foregroundStyle(Color.brieflyBrand)

            Text(viewModel.loggedInEmail)
                .font(.subheadline)
                .foregroundStyle(Color.brieflyTextSecondary)

            Button(role: .destructive) {
                viewModel.logout()
            } label: {
                Label("로그아웃", systemImage: "rectangle.portrait.and.arrow.right")
            }
            .buttonStyle(.bordered)
            .padding(.top, 8)
        }
        .padding()
    }

    // MARK: - 로그인 폼

    private var loginView: some View {
        ScrollView {
            VStack(spacing: 28) {
                VStack(spacing: 8) {
                    Image(systemName: "person.circle")
                        .font(.system(size: 64))
                        .foregroundStyle(Color.brieflyInk300)
                    Text("Briefly에 로그인")
                        .font(.brieflyH2)
                        .foregroundStyle(Color.brieflyTextPrimary)
                    Text("저장한 링크를 모든 기기에서 동기화합니다")
                        .font(.subheadline)
                        .foregroundStyle(Color.brieflyTextSecondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.top, 32)

                VStack(spacing: 12) {
                    TextField("이메일", text: $viewModel.emailInput)
                        .textFieldStyle(.roundedBorder)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()

                    SecureField("비밀번호", text: $viewModel.passwordInput)
                        .textFieldStyle(.roundedBorder)
                }
                .padding(.horizontal, 24)

                if viewModel.isLoading {
                    ProgressView()
                } else {
                    VStack(spacing: 12) {
                        Button {
                            viewModel.login()
                        } label: {
                            Text("로그인")
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 4)
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(Color.brieflyPrimary500)
                        .disabled(viewModel.emailInput.isEmpty || viewModel.passwordInput.isEmpty)

                        HStack {
                            Rectangle().frame(height: 1).foregroundStyle(Color.brieflyBorder)
                            Text("또는").font(.caption).foregroundStyle(Color.brieflyInk400)
                            Rectangle().frame(height: 1).foregroundStyle(Color.brieflyBorder)
                        }

                        Button {
                            viewModel.signInWithGoogle()
                        } label: {
                            HStack(spacing: 8) {
                                GoogleGLogo(size: 18)
                                Text("Google로 로그인")
                                    .foregroundStyle(Color.brieflyTextPrimary)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 4)
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding(.horizontal, 24)
                }
            }
        }
    }
}

// MARK: - ViewModel

@MainActor
final class AuthViewModel: ObservableObject {
    @Published var isLoggedIn: Bool = AuthTokenStore.shared.isLoggedIn
    @Published var loggedInEmail: String = AuthTokenStore.shared.email ?? ""
    @Published var emailInput: String = ""
    @Published var passwordInput: String = ""
    @Published var isLoading = false
    @Published var showError = false
    @Published var errorMessage: String?


    func login() {
        guard !emailInput.isEmpty, !passwordInput.isEmpty else { return }
        isLoading = true
        Task {
            defer { isLoading = false }
            do {
                let result = try await BrieflyAPI.shared.loginWithEmail(
                    email: emailInput,
                    password: passwordInput
                )
                AuthTokenStore.shared.save(
                    accessToken: result.accessToken,
                    refreshToken: result.refreshToken,
                    userId: result.userId,
                    displayName: nil,
                    email: result.email
                )
                loggedInEmail = result.email
                isLoggedIn = true
                passwordInput = ""
                Task { await SyncService.shared.syncLocalItemsToServer() }
            } catch let error as BrieflyAPI.APIError {
                switch error {
                case .httpError(401, _):
                    presentError("이메일 또는 비밀번호가 올바르지 않습니다.")
                case .httpError(403, _):
                    presentError("이메일 인증이 완료되지 않았습니다. 받은 메일함을 확인해 주세요.")
                default:
                    presentError("로그인 실패: \(error.localizedDescription)")
                }
            } catch {
                presentError("로그인 실패: \(error.localizedDescription)")
            }
        }
    }

    func signInWithGoogle() {
        guard let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let rootVC = windowScene.windows.first?.rootViewController else { return }
        isLoading = true
        Task {
            defer { isLoading = false }
            do {
                let result = try await GIDSignIn.sharedInstance.signIn(withPresenting: rootVC)
                guard let idToken = result.user.idToken?.tokenString else {
                    presentError("Google ID 토큰을 가져올 수 없습니다.")
                    return
                }
                let profile = result.user.profile
                let loginResult = try await BrieflyAPI.shared.loginWithGoogle(
                    idToken: idToken,
                    userID: result.user.userID ?? "",
                    email: profile?.email ?? "",
                    name: profile?.name,
                    picture: profile?.imageURL(withDimension: 120)?.absoluteString
                )
                AuthTokenStore.shared.save(
                    accessToken: loginResult.accessToken,
                    refreshToken: loginResult.refreshToken,
                    userId: loginResult.user.id,
                    displayName: loginResult.user.displayName,
                    email: loginResult.user.email
                )
                loggedInEmail = loginResult.user.email
                isLoggedIn = true
                Task { await SyncService.shared.syncLocalItemsToServer() }
            } catch let error as NSError
                where error.domain == "com.google.GIDSignIn" && error.code == -5 {
                // 사용자 취소 — 에러 없이 무시
            } catch let error as BrieflyAPI.APIError {
                switch error {
                case .httpError(403, _):
                    presentError("계정 삭제 후 30일 내 재가입 불가합니다.")
                default:
                    presentError("Google 로그인 실패: \(error.localizedDescription)")
                }
            } catch {
                presentError("Google 로그인 실패: \(error.localizedDescription)")
            }
        }
    }

    func logout() {
        AuthTokenStore.shared.clear()
        isLoggedIn = false
        loggedInEmail = ""
        emailInput = ""
        passwordInput = ""
    }

    private func presentError(_ message: String) {
        errorMessage = message
        showError = true
    }
}

// MARK: - Google G Logo

private struct GoogleGLogo: View {
    var size: CGFloat = 18

    var body: some View {
        // 웹과 동일한 공식 Google SVG path (viewBox 0 0 18 18)
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

// MARK: - Dev Server Sheet (DEBUG only)

#if DEBUG
private struct DevServerSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var urlInput: String = UserDefaults.standard.string(forKey: BrieflyAPI.devURLKey) ?? BrieflyAPI.defaultDevURL

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("https://xxxx.trycloudflare.com/api/v1", text: $urlInput)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                } header: {
                    Text("백엔드 URL")
                } footer: {
                    Text("저장 후 앱을 재시작하면 적용돼요.")
                }

                Section {
                    Button("기본값으로 초기화") {
                        urlInput = BrieflyAPI.defaultDevURL
                    }
                    .foregroundStyle(Color.brieflyInk400)
                }
            }
            .navigationTitle("서버 설정")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("저장") {
                        Task {
                            await BrieflyAPI.shared.updateBaseURL(urlInput)
                            await MainActor.run { dismiss() }
                        }
                    }
                }
                ToolbarItem(placement: .cancellationAction) {
                    Button("취소") { dismiss() }
                }
            }
        }
    }
}
#endif

#Preview {
    NavigationStack { AccountView() }
}

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

// MARK: - Dev Server Sheet (DEBUG only)

#if DEBUG
private struct DevServerSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var urlInput: String = UserDefaults.standard.string(forKey: BrieflyAPI.devURLKey) ?? BrieflyAPI.defaultDebugURL
    @State private var validationError: String?

    private var isValid: Bool {
        BrieflyAPI.validateBaseURLString(urlInput) != nil
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("https://xxxx.trycloudflare.com/api/v1", text: $urlInput)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .onChange(of: urlInput) { _ in validationError = nil }
                } header: {
                    Text("백엔드 URL")
                } footer: {
                    VStack(alignment: .leading, spacing: 4) {
                        if let validationError {
                            Text(validationError)
                                .foregroundStyle(Color.brieflyError)
                        }
                        Text("필수: http/https scheme + /api/v1 경로. 저장하면 다음 API 호출부터 즉시 적용됩니다.")
                    }
                }

                Section {
                    Button("기본값으로 초기화") {
                        urlInput = BrieflyAPI.defaultDebugURL
                        validationError = nil
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
                            let ok = await BrieflyAPI.shared.updateBaseURL(urlInput)
                            await MainActor.run {
                                if ok {
                                    dismiss()
                                } else {
                                    validationError = "유효한 URL이 아닙니다 (http/https + /api/v1 필요)"
                                }
                            }
                        }
                    }
                    .disabled(!isValid)
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

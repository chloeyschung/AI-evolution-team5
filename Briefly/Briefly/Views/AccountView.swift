import SwiftUI

struct AccountView: View {
    @StateObject private var viewModel = AuthViewModel()

    var body: some View {
        Group {
            if viewModel.isLoggedIn {
                loggedInView
            } else {
                loginView
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .navigationTitle("Account")
        .navigationBarTitleDisplayMode(.large)
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
                .foregroundStyle(.blue)

            Text(viewModel.loggedInEmail)
                .font(.subheadline)
                .foregroundStyle(.secondary)

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
                        .foregroundStyle(.secondary)
                    Text("Briefly에 로그인")
                        .font(.title3.bold())
                    Text("저장한 링크를 모든 기기에서 동기화합니다")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
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
                        .disabled(viewModel.emailInput.isEmpty || viewModel.passwordInput.isEmpty)

                        HStack {
                            Rectangle().frame(height: 1).foregroundStyle(Color(UIColor.separator))
                            Text("또는").font(.caption).foregroundStyle(.secondary)
                            Rectangle().frame(height: 1).foregroundStyle(Color(UIColor.separator))
                        }

                        Button {
                            viewModel.signInWithGoogle()
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: "globe")
                                    .foregroundStyle(.primary)
                                Text("Google로 로그인")
                                    .foregroundStyle(.primary)
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
        // GoogleService-Info.plist 및 OAuth 설정 완료 후 활성화 예정 (TODOS.md 참조)
        presentError("Google 로그인은 OAuth 설정 완료 후 사용 가능합니다.")
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

#Preview {
    NavigationStack { AccountView() }
}

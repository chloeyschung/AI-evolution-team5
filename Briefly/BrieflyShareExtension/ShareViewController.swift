import UIKit
import UniformTypeIdentifiers
import SwiftUI

/// Action Extension 진입점 (com.apple.ui-services).
/// Safari 등 외부 앱에서 URL을 공유하면 이 뷰컨트롤러가 호출됩니다.
///
/// 흐름:
/// 1. 첨부파일에서 URL 추출 (public.url → public.plain-text 순서로 시도)
/// 2. App Group UserDefaults inbox에 SavedItem 추가 + synchronize()
/// 3. 확인 UI 표시 ("닫기" / "지금 읽기" 버튼, 3초 후 자동 닫기)
/// 4. "지금 읽기" → briefly://item?url=… 로 메인 앱 오픈 (Library 탭 + 해당 아이템 상세)
final class ShareViewController: UIViewController {

    private var autoDismissTimer: DispatchWorkItem?

    // MARK: - Lifecycle

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        extractURLAndSave()
    }

    // MARK: - URL 추출 + 저장

    private func extractURLAndSave() {
        guard
            let item = extensionContext?.inputItems.first as? NSExtensionItem,
            let attachments = item.attachments,
            !attachments.isEmpty
        else {
            showConfirmation(success: false)
            return
        }
        findURL(in: attachments)
    }

    /// public.url → public.plain-text 순으로 URL을 탐색합니다.
    private func findURL(in providers: [NSItemProvider]) {
        if let provider = providers.first(where: { $0.hasItemConformingToTypeIdentifier(UTType.url.identifier) }) {
            provider.loadItem(forTypeIdentifier: UTType.url.identifier) { [weak self] item, _ in
                if let url = item as? URL, url.scheme?.hasPrefix("http") == true {
                    self?.saveAndShow(url: url)
                } else {
                    self?.tryPlainText(in: providers)
                }
            }
        } else {
            tryPlainText(in: providers)
        }
    }

    private func tryPlainText(in providers: [NSItemProvider]) {
        guard let provider = providers.first(where: { $0.hasItemConformingToTypeIdentifier(UTType.plainText.identifier) }) else {
            DispatchQueue.main.async { self.showConfirmation(success: false) }
            return
        }
        provider.loadItem(forTypeIdentifier: UTType.plainText.identifier) { [weak self] item, _ in
            let text = (item as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if let url = URL(string: text), url.scheme?.hasPrefix("http") == true {
                self?.saveAndShow(url: url)
            } else {
                DispatchQueue.main.async { self?.showConfirmation(success: false) }
            }
        }
    }

    private func saveAndShow(url: URL) {
        var item = SavedItem(url: url, title: nil)
        StorageService.shared.appendToInbox(item)

        // 로그인된 경우 백엔드에도 전송하고 serverContentId를 저장
        if let token = AuthTokenStore.shared.accessToken {
            Task {
                if let result = try? await BrieflyAPI.shared.share(url: url, token: token) {
                    item.serverContentId = result.id
                    StorageService.shared.updateItemById(item)
                }
            }
        }

        DispatchQueue.main.async {
            self.showConfirmation(success: true, savedURL: url)
        }
    }

    // MARK: - 확인 UI

    private func showConfirmation(success: Bool, savedURL: URL? = nil) {
        let confirmView = ConfirmationView(
            success: success,
            domain: savedURL?.host ?? "",
            onDismiss: { [weak self] in
                self?.cancelTimerAndComplete()
            },
            onReadNow: savedURL.map { url in
                { [weak self] in self?.openMainApp(articleURL: url) }
            }
        )

        let host = UIHostingController(rootView: confirmView)
        host.view.backgroundColor = .clear
        addChild(host)
        view.addSubview(host.view)
        host.view.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            host.view.topAnchor.constraint(equalTo: view.topAnchor),
            host.view.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            host.view.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            host.view.trailingAnchor.constraint(equalTo: view.trailingAnchor),
        ])
        host.didMove(toParent: self)

        // 3초 후 자동 닫기 (버튼 탭 시 취소됨)
        let timer = DispatchWorkItem { [weak self] in self?.completeRequest() }
        autoDismissTimer = timer
        DispatchQueue.main.asyncAfter(deadline: .now() + 3, execute: timer)
    }

    // MARK: - 액션

    private func cancelTimerAndComplete() {
        autoDismissTimer?.cancel()
        completeRequest()
    }

    private func openMainApp(articleURL: URL) {
        autoDismissTimer?.cancel()
        var comps = URLComponents()
        comps.scheme = "briefly"
        comps.host = "item"
        comps.queryItems = [URLQueryItem(name: "url", value: articleURL.absoluteString)]
        guard let brieflyURL = comps.url else {
            completeRequest()
            return
        }
        extensionContext?.open(brieflyURL) { [weak self] success in
            if !success {
                print("[ShareViewController] extensionContext.open 실패 — 시뮬레이터 제한일 수 있음")
            }
            self?.completeRequest()
        }
    }

    private func completeRequest() {
        extensionContext?.completeRequest(returningItems: [])
    }
}

// MARK: - SwiftUI 확인 뷰

private struct ConfirmationView: View {
    let success: Bool
    let domain: String
    let onDismiss: () -> Void
    let onReadNow: (() -> Void)?

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: success ? "checkmark.circle.fill" : "xmark.circle.fill")
                .font(.system(size: 48))
                .foregroundStyle(success ? .green : .red)

            if success {
                Text("Briefly에 저장됐어요")
                    .font(.headline)
                if !domain.isEmpty {
                    Text(domain)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                HStack(spacing: 12) {
                    Button("닫기", action: onDismiss)
                        .buttonStyle(.bordered)
                    Button("지금 읽기") { onReadNow?() }
                        .buttonStyle(.borderedProminent)
                }
                .padding(.top, 4)
            } else {
                Text("저장 실패")
                    .font(.headline)
                Text("Briefly 앱을 열어 재시도해주세요")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Button("닫기", action: onDismiss)
                    .buttonStyle(.bordered)
                    .padding(.top, 4)
            }
        }
        .padding(32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(.regularMaterial)
    }
}

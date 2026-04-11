import UIKit
import UniformTypeIdentifiers
import SwiftUI

/// Share Extension 진입점.
/// Safari 등 외부 앱에서 URL을 공유하면 이 뷰컨트롤러가 호출됩니다.
///
/// 흐름:
/// 1. NSExtensionItem에서 URL 추출 (async)
/// 2. App Group UserDefaults inbox에 SavedItem 추가
/// 3. 확인 UI 표시 (1.5초)
/// 4. Extension 닫기
final class ShareViewController: UIViewController {

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
            let provider = item.attachments?.first,
            provider.hasItemConformingToTypeIdentifier(UTType.url.identifier)
        else {
            showConfirmation(success: false)
            return
        }

        provider.loadItem(forTypeIdentifier: UTType.url.identifier) { [weak self] urlItem, error in
            guard let self else { return }

            if let url = urlItem as? URL {
                let savedItem = SavedItem(url: url, title: nil)
                StorageService.shared.appendToInbox(savedItem)
                DispatchQueue.main.async {
                    self.showConfirmation(success: true, url: url)
                }
            } else {
                DispatchQueue.main.async {
                    self.showConfirmation(success: false)
                }
            }
        }
    }

    // MARK: - 확인 UI

    private func showConfirmation(success: Bool, url: URL? = nil) {
        // SwiftUI 확인 뷰를 UIHostingController로 embed
        let confirmView = ConfirmationView(
            success: success,
            domain: url?.host ?? "",
            onDismiss: { [weak self] in
                self?.completeRequest()
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

        // 1.5초 후 자동 닫기
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { [weak self] in
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
            } else {
                Text("저장 실패")
                    .font(.headline)
                Text("Briefly 앱을 열어 재시도해주세요")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(.regularMaterial)
    }
}

import { pageExtractor } from '../utils/extractor';
import { PageMetadata } from '../shared/types';

let metadataCache: PageMetadata | null = null;

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'getMetadata') {
    handleGetMetadata().then(sendResponse);
    return true; // Keep channel open for async response
  }
  return false;
});

async function handleGetMetadata(): Promise<{ metadata: PageMetadata }> {
  if (!metadataCache) {
    metadataCache = await pageExtractor.extractMetadata();
  }
  return { metadata: metadataCache };
}

// Inject save button (optional, for future enhancement)
function injectSaveButton(): void {
  const button = document.createElement('button');
  button.textContent = '💾 Save to Briefly';
  button.className = 'briefly-save-button';
  button.title = 'Save this page to Briefly';

  button.onclick = async () => {
    const metadata = await pageExtractor.extractMetadata();
    const selectedText = pageExtractor.getSelectedText();

    chrome.runtime.sendMessage({
      action: 'saveContent',
      data: { metadata, selectedText },
    }, (response) => {
      if (response?.success) {
        button.classList.add('saved');
        button.textContent = '✅ Saved!';
        setTimeout(() => {
          button.classList.remove('saved');
          button.textContent = '💾 Save to Briefly';
        }, 2000);
      }
    });
  };

  document.body.appendChild(button);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  // Uncomment to enable floating save button
  // injectSaveButton();
});

// Refresh metadata cache on page navigation
window.addEventListener('popstate', () => {
  metadataCache = null;
});

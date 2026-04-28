import { authManager } from '../shared/auth';
import { apiClient } from '../shared/api';
import { PageMetadata, SaveRequest, SaveResult, Notification } from '../shared/types';

// Initialize auth on startup
authManager.initialize();

async function setupContextMenus(): Promise<void> {
  await chrome.contextMenus.removeAll();
  chrome.contextMenus.create({
    id: 'save-to-briefly',
    title: 'Save to Briefly',
    contexts: ['page'],
  });
  chrome.contextMenus.create({
    id: 'save-link-to-briefly',
    title: 'Save link to Briefly',
    contexts: ['link'],
  });
  chrome.contextMenus.create({
    id: 'save-selection-to-briefly',
    title: 'Save Selection to Briefly',
    contexts: ['selection'],
  });
}

// Recreate context menus whenever the worker lifecycle restarts.
chrome.runtime.onInstalled.addListener(() => {
  setupContextMenus().catch((error) => console.error('Failed to initialize context menus:', error));
});
chrome.runtime.onStartup.addListener(() => {
  setupContextMenus().catch((error) => console.error('Failed to initialize context menus:', error));
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const tabId = tab?.id;
  if (!tabId) return;

  try {
    if (!(await authManager.isAuthenticated())) {
      showNotification({
        type: 'error',
        message: 'Please login to Briefly first',
      });
      chrome.action.openPopup();
      return;
    }

    let metadata: PageMetadata;
    let selectedText: string | undefined;

    if (info.menuItemId === 'save-link-to-briefly') {
      // Save the specific link URL, not the current page
      const linkUrl = info.linkUrl || '';
      metadata = {
        url: linkUrl,
        title: null,
        author: null,
        description: null,
        type: 'article',
      };
    } else if (info.menuItemId === 'save-selection-to-briefly') {
      selectedText = info.selectionText;
      metadata = {
        url: tab?.url || '',
        title: tab?.title ?? null,
        author: null,
        description: null,
        type: 'text',
      };
    } else {
      // Try content script first; fall back to tab URL/title if not injected
      try {
        const response = await chrome.tabs.sendMessage(tabId, { action: 'getMetadata' });
        const liveTab = await chrome.tabs.get(tabId);
        const liveUrl = liveTab.pendingUrl || liveTab.url || tab?.url || '';
        metadata = {
          ...(response.metadata as PageMetadata),
          // Ensure final save uses current tab URL (not stale cached metadata URL).
          url: liveUrl,
          title: (response.metadata as PageMetadata)?.title ?? liveTab.title ?? tab?.title ?? null,
        };
      } catch {
        metadata = {
          url: tab?.url || '',
          title: tab?.title ?? null,
          author: null,
          description: null,
          type: 'unknown',
        };
      }
    }

    const result = await apiClient.shareContent(metadata, selectedText);

    showNotification({
      type: 'success',
      message: `Saved: ${result.title || 'Content'}`,
    });
  } catch (error) {
    console.error('Error saving content:', error);
    showNotification({
      type: 'error',
      message: error instanceof Error ? error.message : 'Failed to save content. Please try again.',
    });
  }
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'saveContent') {
    handleSaveContent(message.data).then(sendResponse);
    return true; // Keep message channel open for async response
  }
  return false;
});

async function handleSaveContent(data: SaveRequest): Promise<SaveResult> {
  try {
    if (!(await authManager.isAuthenticated())) {
      return {
        success: false,
        error: 'Not authenticated',
      };
    }

    const result = await apiClient.shareContent(data.metadata, data.selectedText);

    showNotification({
      type: 'success',
      message: `Saved: ${result.title || 'Content'}`,
    });

    return { success: true, data: result };
  } catch (error) {
    console.error('Error in handleSaveContent:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

function showNotification(notification: Notification): void {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: 'Briefly',
    message: notification.message,
    priority: notification.type === 'error' ? 2 : 1,
  });
}

// Handle action icon clicks - open popup
chrome.action.onClicked.addListener(() => {
  chrome.action.openPopup();
});

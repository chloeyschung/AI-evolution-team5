import { authManager } from '../shared/auth';
import { apiClient } from '../shared/api';
import { PageMetadata, SaveRequest, SaveResult, Notification } from '../shared/types';

// Initialize auth on startup
authManager.initialize();

// Create context menu on installation
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'save-to-briefly',
    title: 'Save to Briefly',
    contexts: ['page'],
  });

  chrome.contextMenus.create({
    id: 'save-selection-to-briefly',
    title: 'Save Selection to Briefly',
    contexts: ['selection'],
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab.id) return;

  try {
    await authManager.initialize();

    if (!(await authManager.isAuthenticated())) {
      this.showNotification({
        type: 'error',
        message: 'Please login to Briefly first',
      });
      chrome.action.openPopup();
      return;
    }

    let metadata: PageMetadata;
    let selectedText: string | undefined;

    if (info.menuItemId === 'save-selection-to-briefly') {
      selectedText = info.selectionText;
      metadata = {
        url: tab.url || '',
        title: tab.title,
        author: null,
        description: null,
        type: 'text',
      };
    } else {
      // Get metadata from content script
      const response = await chrome.tabs.sendMessage(tab.id, { action: 'getMetadata' });
      metadata = response.metadata;
    }

    const result = await apiClient.shareContent(metadata, selectedText);

    this.showNotification({
      type: 'success',
      message: `Saved: ${result.title || 'Content'}`,
    });
  } catch (error) {
    console.error('Error saving content:', error);
    this.showNotification({
      type: 'error',
      message: 'Failed to save content. Please try again.',
    });
  }
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'saveContent') {
    this.handleSaveContent(message.data, sender as chrome.tabs.Tab).then(sendResponse);
    return true; // Keep message channel open for async response
  }
  return false;
});

async function handleSaveContent(data: SaveRequest, tab: chrome.tabs.Tab): Promise<SaveResult> {
  try {
    await authManager.initialize();

    if (!(await authManager.isAuthenticated())) {
      return {
        success: false,
        error: 'Not authenticated',
      };
    }

    const result = await apiClient.shareContent(data.metadata, data.selectedText);

    this.showNotification({
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
chrome.action.onClicked.addListener((tab) => {
  chrome.action.openPopup();
});

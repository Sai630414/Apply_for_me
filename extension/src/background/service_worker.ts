/**
 * ApplyForMe Background Service Worker (Manifest V3)
 * Handles cross-origin backend API communication, script injection, and badge management.
 */

const DEFAULT_API_BASE = 'http://localhost:8000/api';

async function getBaseUrl(): Promise<string> {
  return new Promise((resolve) => {
    chrome.storage.local.get(['custom_api_url'], (res) => {
      resolve(res.custom_api_url ? res.custom_api_url.replace(/\/+$/, '') : DEFAULT_API_BASE);
    });
  });
}

async function getAuthToken(): Promise<string | null> {
  return new Promise((resolve) => {
    chrome.storage.local.get(['auth_token'], (res) => {
      resolve(res.auth_token || null);
    });
  });
}

chrome.runtime.onInstalled.addListener(() => {
  console.log('[ApplyForMe] Service worker installed.');
  chrome.action.setBadgeBackgroundColor({ color: '#4f46e5' });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // 1. Badge notification from content script
  if (message.type === 'FORM_DETECTED') {
    const tabId = sender.tab?.id;
    if (tabId) {
      chrome.action.setBadgeText({ tabId, text: String(message.count || 'FORM') });
      chrome.action.setBadgeBackgroundColor({ tabId, color: '#10b981' });
    }
    sendResponse({ received: true });
    return true;
  }

  // 2. Clear badge
  if (message.type === 'CLEAR_BADGE') {
    const tabId = sender.tab?.id;
    if (tabId) {
      chrome.action.setBadgeText({ tabId, text: '' });
    }
    sendResponse({ received: true });
    return true;
  }

  // 3. Open full Dashboard
  if (message.type === 'OPEN_DASHBOARD') {
    chrome.tabs.create({ url: chrome.runtime.getURL('dashboard.html') });
    sendResponse({ success: true });
    return true;
  }

  // 4. Ping check
  if (message.type === 'PING') {
    sendResponse({ status: 'ok', worker: true });
    return true;
  }

  // 5. Proxy API request: Map form fields
  // Service worker has full host_permissions and is immune to page CSP / Mixed Content
  if (message.type === 'MAP_FIELDS') {
    (async () => {
      try {
        const baseUrl = await getBaseUrl();
        const token = await getAuthToken();

        if (!token) {
          sendResponse({
            success: false,
            error: 'Authentication required. Please sign in to ApplyForMe first.'
          });
          return;
        }

        const res = await fetch(`${baseUrl}/autofill/map-fields`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            fields: message.fields,
            companyName: message.companyName || '',
            jobTitle: message.jobTitle || '',
            jobDescription: message.jobDescription || '',
            url: message.url || ''
          })
        });

        if (!res.ok) {
          const errBody = await res.text();
          let msg = `Server error ${res.status}`;
          try {
            const parsed = JSON.parse(errBody);
            msg = parsed.detail || msg;
          } catch {}
          sendResponse({ success: false, error: msg });
          return;
        }

        const data = await res.json();
        sendResponse({ success: true, data });
      } catch (err: any) {
        sendResponse({
          success: false,
          error: err.message || 'Failed to connect to ApplyForMe backend at http://localhost:8000.'
        });
      }
    })();
    return true;
  }

  // 6. Ensure Content Script Injected
  if (message.type === 'INJECT_CONTENT_SCRIPT') {
    const tabId = message.tabId;
    if (!tabId) {
      sendResponse({ success: false, error: 'No tab ID specified' });
      return true;
    }

    chrome.scripting.executeScript(
      {
        target: { tabId },
        files: ['src/content/content_script.js']
      },
      () => {
        if (chrome.runtime.lastError) {
          sendResponse({ success: false, error: chrome.runtime.lastError.message });
        } else {
          sendResponse({ success: true });
        }
      }
    );
    return true;
  }
});

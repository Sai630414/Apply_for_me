/**
 * Unified storage wrapper supporting both chrome.storage.local
 * and window.localStorage (for standalone development/testing preview).
 */

const isChromeStorage = typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local;

export const storage = {
  async get<T = any>(key: string): Promise<T | null> {
    if (isChromeStorage) {
      return new Promise((resolve) => {
        chrome.storage.local.get([key], (result) => {
          resolve(result[key] !== undefined ? result[key] : null);
        });
      });
    } else {
      const item = localStorage.getItem(key);
      if (item === null) return null;
      try {
        return JSON.parse(item) as T;
      } catch {
        return item as unknown as T;
      }
    }
  },

  async set(key: string, value: any): Promise<void> {
    if (isChromeStorage) {
      return new Promise((resolve) => {
        chrome.storage.local.set({ [key]: value }, () => resolve());
      });
    } else {
      localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value));
    }
  },

  async remove(key: string): Promise<void> {
    if (isChromeStorage) {
      return new Promise((resolve) => {
        chrome.storage.local.remove([key], () => resolve());
      });
    } else {
      localStorage.removeItem(key);
    }
  },

  async clear(): Promise<void> {
    if (isChromeStorage) {
      return new Promise((resolve) => {
        chrome.storage.local.clear(() => resolve());
      });
    } else {
      localStorage.clear();
    }
  }
};


import { FormDetector } from './form_detector';
import { AutofillEngine } from './autofill_engine';
import { JobContextExtractor } from './job_context_extractor';
import { FormFieldMapping, AutofillResult } from '../lib/types';

// Guard against multiple initializations in the same frame
if ((window as any).__APPLYFORME_INITIALIZED__) {
  console.log('[ApplyForMe] Content script already initialized in frame.');
} else {
  (window as any).__APPLYFORME_INITIALIZED__ = true;

  console.log('[ApplyForMe] Content script successfully loaded.');

  let lastDismissedUrl = '';
  let isOverlayActive = false;

  function showOverlay(fieldsCount: number) {
    if (isOverlayActive || document.getElementById('applyforme-floating-overlay')) {
      return;
    }

    if (window.location.href === lastDismissedUrl) {
      return;
    }

    isOverlayActive = true;
    const ctx = JobContextExtractor.extract();
    const contextTitle = ctx.companyName
      ? `${ctx.companyName}${ctx.jobTitle ? ' · ' + ctx.jobTitle : ''}`
      : 'Job Application Form Detected';

    const overlay = document.createElement('div');
    overlay.id = 'applyforme-floating-overlay';
    overlay.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 2147483647;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.08);
      padding: 14px 18px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      align-items: center;
      gap: 16px;
      animation: afm-fade-in 0.3s ease;
    `;

    overlay.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:34px;height:34px;background:linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:15px;box-shadow:0 2px 6px rgba(79,70,229,0.3);">
          A
        </div>
        <div>
          <div style="font-weight:600;font-size:13px;color:#0f172a;line-height:1.2;">${contextTitle}</div>
          <div style="font-size:11px;color:#64748b;margin-top:2px;">${fieldsCount} fields detected. Autofill with AI & profile?</div>
        </div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <button id="afm-autofill-btn" style="background:#4f46e5;color:#ffffff;border:none;border-radius:6px;padding:7px 14px;font-size:12px;font-weight:600;cursor:pointer;transition:background 0.15s ease;">
          Autofill with AI
        </button>
        <button id="afm-dismiss-btn" style="background:#f8fafc;color:#64748b;border:1px solid #cbd5e1;border-radius:6px;padding:7px 10px;font-size:12px;cursor:pointer;" title="Dismiss">
          ✕
        </button>
      </div>
    `;

    document.body.appendChild(overlay);

    document.getElementById('afm-dismiss-btn')?.addEventListener('click', () => {
      lastDismissedUrl = window.location.href;
      isOverlayActive = false;
      overlay.remove();
    });

    document.getElementById('afm-autofill-btn')?.addEventListener('click', async () => {
      const btn = document.getElementById('afm-autofill-btn') as HTMLButtonElement;
      if (btn) {
        btn.innerText = 'Generating & Filling...';
        btn.disabled = true;
      }
      const result = await triggerAutofill();
      if (result.totalFilled > 0) {
        btn.innerText = `Filled ${result.totalFilled} fields!`;
        btn.style.background = '#10b981';
        setTimeout(() => {
          overlay.remove();
          isOverlayActive = false;
        }, 2500);
      } else {
        btn.innerText = result.message || 'No fields filled';
        btn.style.background = '#f59e0b';
        setTimeout(() => {
          overlay.remove();
          isOverlayActive = false;
        }, 3000);
      }
    });
  }

  /**
   * Execute end-to-end autofill:
   * 1. Detect all fields on current webpage DOM
   * 2. Extract job context (Company, Title, Description)
   * 3. Send detected fields to background service worker
   * 4. Apply verified mappings via AutofillEngine
   */
  async function triggerAutofill(providedMappings?: FormFieldMapping[]): Promise<AutofillResult> {
    try {
      const fields = FormDetector.detectFields();
      if (fields.length === 0) {
        return {
          success: false,
          totalDetected: 0,
          totalMapped: 0,
          totalFilled: 0,
          skipped: 0,
          failed: 0,
          fields: [],
          message: 'No form fields detected on this page.'
        };
      }

      let mappings: FormFieldMapping[] = providedMappings || [];
      if (!providedMappings || providedMappings.length === 0) {
        const ctx = JobContextExtractor.extract();

        // Request mappings from background service worker with extracted context
        const mapRes: any = await new Promise((resolve) => {
          chrome.runtime.sendMessage({
            type: 'MAP_FIELDS',
            fields,
            companyName: ctx.companyName,
            jobTitle: ctx.jobTitle,
            jobDescription: ctx.jobDescription,
            url: ctx.url
          }, (res) => {
            if (chrome.runtime.lastError) {
              resolve({ success: false, error: chrome.runtime.lastError.message });
            } else {
              resolve(res);
            }
          });
        });

        if (!mapRes || !mapRes.success) {
          return {
            success: false,
            totalDetected: fields.length,
            totalMapped: 0,
            totalFilled: 0,
            skipped: 0,
            failed: fields.length,
            fields: [],
            message: mapRes?.error || 'Failed to map form fields. Please ensure backend is running.'
          };
        }
        mappings = (mapRes.data?.mappings || []) as FormFieldMapping[];
      }

      const result = AutofillEngine.applyMappings(mappings);
      return result;
    } catch (err: any) {
      console.error('[ApplyForMe] Autofill runtime error:', err);
      return {
        success: false,
        totalDetected: 0,
        totalMapped: 0,
        totalFilled: 0,
        skipped: 0,
        failed: 0,
        fields: [],
        message: err.message || 'Error occurred during autofill execution.'
      };
    }
  }

  function scanForApplication() {
    try {
      const fields = FormDetector.detectFields();
      const isJobForm = FormDetector.isApplicationForm(fields);

      if (isJobForm && fields.length > 0) {
        const ctx = JobContextExtractor.extract();
        try {
          chrome.runtime.sendMessage({
            type: 'FORM_DETECTED',
            count: fields.length,
            url: window.location.href,
            title: document.title,
            companyName: ctx.companyName,
            jobTitle: ctx.jobTitle
          });
        } catch {}

        showOverlay(fields.length);
      }
    } catch (err) {
      console.warn('[ApplyForMe] Scan error:', err);
    }
  }

  // Initial scan after DOM stabilization
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(scanForApplication, 800));
  } else {
    setTimeout(scanForApplication, 800);
  }

  // MutationObserver with debounce for dynamic SPA changes (React/Vue/Angular)
  let mutationTimer: any = null;
  const observer = new MutationObserver(() => {
    if (mutationTimer) clearTimeout(mutationTimer);
    mutationTimer = setTimeout(scanForApplication, 1200);
  });

  const startObserver = () => {
    if (document.body) {
      observer.observe(document.body, { childList: true, subtree: true });
    }
  };

  if (document.body) {
    startObserver();
  } else {
    document.addEventListener('DOMContentLoaded', startObserver);
  }

  // Track SPA navigation (pushState, replaceState, popstate)
  window.addEventListener('popstate', () => {
    setTimeout(scanForApplication, 500);
  });

  const originalPushState = history.pushState;
  history.pushState = function (...args) {
    originalPushState.apply(this, args);
    setTimeout(scanForApplication, 500);
  };

  const originalReplaceState = history.replaceState;
  history.replaceState = function (...args) {
    originalReplaceState.apply(this, args);
    setTimeout(scanForApplication, 500);
  };

  // Message listener for popup & background
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'PING') {
      sendResponse({ status: 'ok', script: true });
      return true;
    }

    if (request.action === 'DETECT_APPLICATION') {
      const fields = FormDetector.detectFields();
      const isJobForm = FormDetector.isApplicationForm(fields);
      const jobContext = JobContextExtractor.extract();
      sendResponse({ isJobForm, fieldsCount: fields.length, fields, jobContext });
      return true;
    }

    if (request.action === 'GET_JOB_CONTEXT') {
      sendResponse(JobContextExtractor.extract());
      return true;
    }

    if (request.action === 'START_AUTOFILL') {
      triggerAutofill(request.mappings).then((result) => {
        sendResponse(result);
      });
      return true; // Keep channel open for async response
    }
  });
}

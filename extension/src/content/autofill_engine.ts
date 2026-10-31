import { FormFieldMapping, AutofillResult, FieldFillResult } from '../lib/types';

export class AutofillEngine {
  /**
   * Set input/textarea value in a way that React, Vue, Angular and standard DOM detect.
   */
  private static setNativeValue(element: HTMLInputElement | HTMLTextAreaElement, value: string): void {
    const prototype = element instanceof HTMLInputElement
      ? window.HTMLInputElement.prototype
      : window.HTMLTextAreaElement.prototype;

    const descriptor = Object.getOwnPropertyDescriptor(prototype, 'value');
    if (descriptor && descriptor.set) {
      descriptor.set.call(element, value);
    } else {
      element.value = value;
    }

    // Reset React's internal value tracker so React detects the update
    const tracker = (element as any)._valueTracker;
    if (tracker) {
      tracker.setValue('');
    }

    // Dispatch synthetic bubbling input and change events
    element.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
    element.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
    element.dispatchEvent(new Event('blur', { bubbles: true, composed: true }));
  }

  /**
   * Locate target element by selector (data-applyforme-id), ID, or Name.
   */
  private static findElement(m: FormFieldMapping): HTMLElement | null {
    if (m.selector) {
      try {
        const el = document.querySelector<HTMLElement>(m.selector);
        if (el) return el;
      } catch {}
    }

    if (m.elementIdentifier) {
      // Try ID
      try {
        const elById = document.getElementById(m.elementIdentifier);
        if (elById) return elById;
      } catch {}

      // Try Name
      try {
        const elByName = document.querySelector<HTMLElement>(`[name="${CSS.escape(m.elementIdentifier)}"]`);
        if (elByName) return elByName;
      } catch {}

      // Try Selector
      try {
        const elBySel = document.querySelector<HTMLElement>(m.elementIdentifier);
        if (elBySel) return elBySel;
      } catch {}
    }

    return null;
  }

  /**
   * Inject highlight CSS styles into document head if not already present.
   */
  private static ensureHighlightStyle(): void {
    if (!document.getElementById('applyforme-highlight-style')) {
      const style = document.createElement('style');
      style.id = 'applyforme-highlight-style';
      style.textContent = `
        .applyforme-filled-highlight,
        .applyforme-profile-highlight {
          outline: 2px solid #10b981 !important;
          background-color: #f0fdf4 !important;
          transition: background-color 0.4s ease, outline 0.4s ease;
        }
        .applyforme-ai-highlight {
          outline: 2px solid #8b5cf6 !important;
          background-color: #f5f3ff !important;
          transition: background-color 0.4s ease, outline 0.4s ease;
        }
        .applyforme-review-highlight {
          outline: 2px dashed #f59e0b !important;
          background-color: #fffbeb !important;
          transition: background-color 0.4s ease, outline 0.4s ease;
        }
      `;
      document.head.appendChild(style);
    }
  }

  static applyMappings(mappings: FormFieldMapping[]): AutofillResult {
    this.ensureHighlightStyle();

    const fieldsResults: FieldFillResult[] = [];
    let filled = 0;
    let skipped = 0;
    let failed = 0;
    let directMappedCount = 0;
    let aiGeneratedCount = 0;
    let userInputRequiredCount = 0;

    for (const m of mappings) {
      const fieldDisplayName = m.fieldName || m.elementIdentifier || 'Field';
      const category = m.category || 'DIRECT_PROFILE_FIELD';

      // 1. Explicit Consent & Legal check - NEVER automatically accept
      if (category === 'CONSENT_OR_LEGAL') {
        skipped++;
        fieldsResults.push({
          name: fieldDisplayName,
          elementIdentifier: m.elementIdentifier,
          selector: m.selector,
          status: 'skipped',
          category,
          reason: 'Legal declarations and consent checkboxes must be manually checked by applicant'
        });
        continue;
      }

      // 2. User Input / Confirmation Required (missing data or unconfirmed)
      const isUnconfirmed = Boolean(m.requiresReview || m.requires_confirmation);
      const hasValue = m.fillValue !== undefined && m.fillValue !== null && String(m.fillValue).trim() !== '';

      if (!hasValue || (isUnconfirmed && (category === 'USER_INPUT_REQUIRED' || category === 'USER_CONFIRMATION_REQUIRED' || category === 'UNSUPPORTED' || category === 'UNSUPPORTED_FIELD'))) {
        userInputRequiredCount++;
        skipped++;
        const elReview = this.findElement(m);
        if (elReview) {
          elReview.classList.add('applyforme-review-highlight');
        }
        fieldsResults.push({
          name: fieldDisplayName,
          elementIdentifier: m.elementIdentifier,
          selector: m.selector,
          status: 'skipped',
          category: 'USER_CONFIRMATION_REQUIRED',
          reason: m.confirmation_reason || m.reason || 'Missing profile data or user confirmation required'
        });
        continue;
      }

      // 3. Locate element in DOM
      const el = this.findElement(m);
      if (!el) {
        failed++;
        fieldsResults.push({
          name: fieldDisplayName,
          elementIdentifier: m.elementIdentifier,
          selector: m.selector,
          status: 'failed',
          category,
          reason: 'Element not found on current webpage'
        });
        continue;
      }

      // 4. File input elements - manual selection required
      if (el instanceof HTMLInputElement && el.type === 'file') {
        skipped++;
        fieldsResults.push({
          name: fieldDisplayName,
          elementIdentifier: m.elementIdentifier,
          selector: m.selector,
          status: 'skipped',
          category: 'FILE_UPLOAD',
          reason: 'File upload requires manual file selection due to browser security restrictions'
        });
        continue;
      }

      // 5. Do not overwrite non-empty fields without user permission
      const isRadioOrCheckbox = el instanceof HTMLInputElement && (el.type === 'radio' || el.type === 'checkbox');
      if (!isRadioOrCheckbox) {
        const currentVal = (el as HTMLInputElement).value;
        if (currentVal && currentVal.trim() !== '') {
          skipped++;
          fieldsResults.push({
            name: fieldDisplayName,
            elementIdentifier: m.elementIdentifier,
            selector: m.selector,
            status: 'skipped',
            category,
            reason: 'Field already contains user content'
          });
          continue;
        }
      }

      const highlightClass = category === 'AI_GENERATED_ANSWER'
        ? 'applyforme-ai-highlight'
        : 'applyforme-profile-highlight';

      try {
        const targetValueStr = String(m.fillValue);

        // 6. Radio Buttons
        if (el instanceof HTMLInputElement && el.type === 'radio') {
          const groupName = el.name;
          let matchedRadio: HTMLInputElement | null = null;

          if (groupName) {
            const group = Array.from(document.querySelectorAll<HTMLInputElement>(`input[type="radio"][name="${CSS.escape(groupName)}"]`));
            const targetLower = targetValueStr.toLowerCase();

            for (const r of group) {
              const rVal = r.value.toLowerCase();
              const rLabel = (r.closest('label')?.textContent || r.getAttribute('aria-label') || '').toLowerCase();
              if (rVal === targetLower || rLabel.includes(targetLower)) {
                matchedRadio = r;
                break;
              }
            }
          }

          const targetRadio = matchedRadio || el;
          targetRadio.checked = true;
          targetRadio.dispatchEvent(new Event('click', { bubbles: true, composed: true }));
          targetRadio.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
          targetRadio.dispatchEvent(new Event('change', { bubbles: true, composed: true }));

          if (targetRadio.checked) {
            targetRadio.classList.add(highlightClass);
            filled++;
            if (category === 'AI_GENERATED_ANSWER') aiGeneratedCount++; else directMappedCount++;
            fieldsResults.push({
              name: fieldDisplayName,
              elementIdentifier: m.elementIdentifier,
              selector: m.selector,
              status: 'filled',
              category,
              value: targetRadio.value
            });
          } else {
            failed++;
            fieldsResults.push({
              name: fieldDisplayName,
              elementIdentifier: m.elementIdentifier,
              selector: m.selector,
              status: 'failed',
              category,
              reason: 'Radio button state could not be verified'
            });
          }
        }

        // 7. Checkboxes
        else if (el instanceof HTMLInputElement && el.type === 'checkbox') {
          const affirmative = ['true', 'yes', '1', 'authorized', 'immediate'].includes(targetValueStr.toLowerCase());
          el.checked = affirmative;
          el.dispatchEvent(new Event('click', { bubbles: true, composed: true }));
          el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
          el.dispatchEvent(new Event('change', { bubbles: true, composed: true }));

          if (el.checked === affirmative) {
            el.classList.add(highlightClass);
            filled++;
            if (category === 'AI_GENERATED_ANSWER') aiGeneratedCount++; else directMappedCount++;
            fieldsResults.push({
              name: fieldDisplayName,
              elementIdentifier: m.elementIdentifier,
              selector: m.selector,
              status: 'filled',
              category,
              value: String(affirmative)
            });
          } else {
            failed++;
            fieldsResults.push({
              name: fieldDisplayName,
              elementIdentifier: m.elementIdentifier,
              selector: m.selector,
              status: 'failed',
              category,
              reason: 'Checkbox state could not be verified'
            });
          }
        }

        // 8. Select Dropdowns
        else if (el.tagName === 'SELECT') {
          const selectEl = el as HTMLSelectElement;
          const targetLower = targetValueStr.toLowerCase();
          let matchedIndex = -1;

          // First pass: exact match on text or value
          for (let i = 0; i < selectEl.options.length; i++) {
            const opt = selectEl.options[i];
            const optText = opt.text.trim().toLowerCase();
            const optVal = opt.value.trim().toLowerCase();
            if (optText === targetLower || optVal === targetLower) {
              matchedIndex = i;
              break;
            }
          }

          // Second pass: boolean synonyms
          if (matchedIndex === -1 && ['yes', 'authorized', 'true'].includes(targetLower)) {
            for (let i = 0; i < selectEl.options.length; i++) {
              const optText = selectEl.options[i].text.trim().toLowerCase();
              if (['yes', 'authorized', 'true', 'eligible'].includes(optText)) {
                matchedIndex = i;
                break;
              }
            }
          }

          // Third pass: contains match
          if (matchedIndex === -1) {
            for (let i = 0; i < selectEl.options.length; i++) {
              const opt = selectEl.options[i];
              const optText = opt.text.trim().toLowerCase();
              const optVal = opt.value.trim().toLowerCase();
              if (optText && (optText.includes(targetLower) || (targetLower.length >= 3 && targetLower.includes(optText)))) {
                matchedIndex = i;
                break;
              }
            }
          }

          if (matchedIndex !== -1) {
            selectEl.selectedIndex = matchedIndex;
            selectEl.value = selectEl.options[matchedIndex].value;
            selectEl.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
            selectEl.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
            selectEl.dispatchEvent(new Event('blur', { bubbles: true, composed: true }));

            if (selectEl.selectedIndex === matchedIndex) {
              selectEl.classList.add(highlightClass);
              filled++;
              if (category === 'AI_GENERATED_ANSWER') aiGeneratedCount++; else directMappedCount++;
              fieldsResults.push({
                name: fieldDisplayName,
                elementIdentifier: m.elementIdentifier,
                selector: m.selector,
                status: 'filled',
                category,
                value: selectEl.options[matchedIndex].text
              });
            } else {
              failed++;
              fieldsResults.push({
                name: fieldDisplayName,
                elementIdentifier: m.elementIdentifier,
                selector: m.selector,
                status: 'failed',
                category,
                reason: 'Select dropdown state failed verification'
              });
            }
          } else {
            skipped++;
            fieldsResults.push({
              name: fieldDisplayName,
              elementIdentifier: m.elementIdentifier,
              selector: m.selector,
              status: 'skipped',
              category,
              reason: `No matching dropdown option for "${targetValueStr}"`
            });
          }
        }

        // 9. Standard Text Inputs & Textareas
        else if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
          const inputEl = el as HTMLInputElement | HTMLTextAreaElement;
          this.setNativeValue(inputEl, targetValueStr);

          // Verification
          if (inputEl.value === targetValueStr || inputEl.value.trim().length > 0) {
            inputEl.classList.add(highlightClass);
            filled++;
            if (category === 'AI_GENERATED_ANSWER') aiGeneratedCount++; else directMappedCount++;
            fieldsResults.push({
              name: fieldDisplayName,
              elementIdentifier: m.elementIdentifier,
              selector: m.selector,
              status: 'filled',
              category,
              value: inputEl.value
            });
          } else {
            failed++;
            fieldsResults.push({
              name: fieldDisplayName,
              elementIdentifier: m.elementIdentifier,
              selector: m.selector,
              status: 'failed',
              category,
              reason: 'Input value was rejected by the page DOM'
            });
          }
        }
      } catch (err: any) {
        failed++;
        fieldsResults.push({
          name: fieldDisplayName,
          elementIdentifier: m.elementIdentifier,
          selector: m.selector,
          status: 'failed',
          category,
          reason: err.message || 'Error occurred while filling element'
        });
      }
    }

    const totalDetected = mappings.length;
    const totalMapped = mappings.filter(m => m.fillValue !== undefined && m.fillValue !== null && m.fillValue !== '').length;
    const isSuccess = filled > 0;

    let message = '';
    if (filled > 0) {
      message = `Autofill complete: ${filled} fields populated (${directMappedCount} profile, ${aiGeneratedCount} AI generated).`;
    } else {
      message = 'No fields were filled. Please check the detected fields and your applicant profile.';
    }

    return {
      success: isSuccess,
      totalDetected,
      totalMapped,
      totalFilled: filled,
      directMappedCount,
      aiGeneratedCount,
      userInputRequiredCount,
      skipped,
      failed,
      fields: fieldsResults,
      message
    };
  }
}

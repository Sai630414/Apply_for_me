import { FormFieldDescriptor } from '../lib/types';

export class FormDetector {
  private static isElementVisible(el: HTMLElement): boolean {
    const inputEl = el as HTMLInputElement;
    const isRadioOrCheckbox = inputEl.type === 'radio' || inputEl.type === 'checkbox';
    if (isRadioOrCheckbox || el.closest('label')) {
      return true;
    }

    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
      return false;
    }

    const rect = el.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      return true;
    }

    if (el.offsetParent !== null) {
      return true;
    }

    if (style.position === 'fixed' || style.position === 'sticky') {
      return true;
    }

    return false;
  }

  private static findLabelForElement(el: HTMLElement): string {
    // 1. Explicit label with matching 'for' attribute
    if (el.id) {
      try {
        const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        if (label && label.textContent) {
          return label.textContent.trim();
        }
      } catch {}
    }

    // 2. Parent label element enclosing this input
    const parentLabel = el.closest('label');
    if (parentLabel && parentLabel.textContent) {
      // Remove text of child inputs to avoid duplicate text
      return parentLabel.textContent.replace(el.textContent || '', '').trim();
    }

    // 3. aria-labelledby attribute
    const ariaLabelledby = el.getAttribute('aria-labelledby');
    if (ariaLabelledby) {
      try {
        const refEl = document.getElementById(ariaLabelledby);
        if (refEl && refEl.textContent) {
          return refEl.textContent.trim();
        }
      } catch {}
    }

    // 4. aria-label attribute
    const ariaLabel = el.getAttribute('aria-label');
    if (ariaLabel) {
      return ariaLabel.trim();
    }

    // 5. Preceding sibling element
    let prev = el.previousElementSibling;
    while (prev) {
      if (['LABEL', 'SPAN', 'P', 'DIV', 'STRONG', 'B'].includes(prev.tagName)) {
        const txt = prev.textContent?.trim();
        if (txt && txt.length > 0 && txt.length < 120) {
          return txt;
        }
      }
      prev = prev.previousElementSibling;
    }

    // 6. Closest field container label / heading
    const container = el.closest('.form-group, .field, .input-group, [class*="field"], [class*="form-item"], [class*="control"], fieldset, td');
    if (container) {
      const containerLabel = container.querySelector('label, [class*="label"], legend, .title');
      if (containerLabel && containerLabel !== el && containerLabel.textContent) {
        const txt = containerLabel.textContent.trim();
        if (txt && txt.length > 0 && txt.length < 120) {
          return txt;
        }
      }
    }

    // 7. Placeholder attribute fallback
    const placeholder = (el as HTMLInputElement).placeholder;
    if (placeholder) {
      return placeholder.trim();
    }

    return '';
  }

  static detectFields(): FormFieldDescriptor[] {
    const selector = 'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"]):not([type="image"]), textarea, select';
    const elements = Array.from(document.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(selector));
    
    const descriptors: FormFieldDescriptor[] = [];

    elements.forEach((el, index) => {
      // Filter out invisible / detached fields
      if (!this.isElementVisible(el)) {
        return;
      }

      // Assign a stable, unique data-applyforme-id so AutofillEngine can locate it reliably
      let uniqueId = el.getAttribute('data-applyforme-id');
      if (!uniqueId) {
        uniqueId = `afm-field-${index}-${Date.now().toString(36)}`;
        el.setAttribute('data-applyforme-id', uniqueId);
      }

      const elementSelector = `[data-applyforme-id="${uniqueId}"]`;
      const label = this.findLabelForElement(el);
      const placeholder = (el as HTMLInputElement).placeholder || '';
      const ariaLabel = el.getAttribute('aria-label') || '';
      const autocomplete = el.getAttribute('autocomplete') || '';
      const name = el.name || '';
      const id = el.id || '';
      const type = (el as HTMLInputElement).type || el.tagName.toLowerCase();

      let options: string[] = [];
      if (el.tagName === 'SELECT') {
        const selectEl = el as HTMLSelectElement;
        options = Array.from(selectEl.options).map(o => o.text.trim() || o.value.trim()).filter(Boolean);
      } else if (type === 'radio' && name) {
        // Collect radio group options
        const group = Array.from(document.querySelectorAll<HTMLInputElement>(`input[type="radio"][name="${CSS.escape(name)}"]`));
        options = group.map(r => {
          const rLabel = this.findLabelForElement(r) || r.value;
          return rLabel.trim();
        }).filter(Boolean);
      }

      descriptors.push({
        elementId: id,
        name: name,
        selector: elementSelector,
        type: type,
        label: label,
        placeholder: placeholder,
        ariaLabel: ariaLabel,
        autocomplete: autocomplete,
        options: options,
        currentValue: (type === 'radio' || type === 'checkbox') ? String((el as HTMLInputElement).checked) : (el.value || '')
      });
    });

    return descriptors;
  }

  static isApplicationForm(fields: FormFieldDescriptor[]): boolean {
    if (fields.length < 2) return false;

    let score = 0;
    const keywords = [
      'name', 'first', 'last', 'full', 'email', 'phone', 'mobile', 'tel',
      'resume', 'cv', 'education', 'university', 'college', 'school',
      'degree', 'major', 'gpa', 'cgpa', 'graduation', 'experience',
      'company', 'job', 'position', 'role', 'title', 'linkedin', 'github',
      'portfolio', 'website', 'address', 'city', 'state', 'zip', 'postal',
      'country', 'salary', 'compensation', 'skills', 'cover letter',
      'sponsorship', 'work authorization', 'notice period', 'gender',
      'race', 'veteran', 'disability', 'availability', 'relocate'
    ];

    for (const f of fields) {
      const combined = `${f.name} ${f.elementId} ${f.label} ${f.placeholder} ${f.ariaLabel} ${f.autocomplete} ${f.type}`.toLowerCase();
      for (const kw of keywords) {
        if (combined.includes(kw)) {
          score += 1;
          break;
        }
      }
    }

    const pageText = `${document.title} ${window.location.href}`.toLowerCase();
    const isJobContext = /job|career|apply|application|intern|position|opening|workday|greenhouse|lever\.co|ashbyhq/.test(pageText);

    if (isJobContext && score >= 1) {
      return true;
    }

    return score >= 2;
  }
}

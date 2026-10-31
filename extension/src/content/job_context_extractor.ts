import { JobContext } from '../lib/types';

export class JobContextExtractor {
  static extract(): JobContext {
    const url = window.location.href;
    let companyName = '';
    let jobTitle = '';
    let jobDescription = '';

    try {
      // 1. Lever-specific extraction
      const leverPostingHeader = document.querySelector('.posting-headline h2');
      if (leverPostingHeader) {
        jobTitle = leverPostingHeader.textContent?.trim() || '';
      }
      const leverLogo = document.querySelector('.main-header-logo img, .main-header-logo');
      if (leverLogo) {
        companyName = (leverLogo as HTMLImageElement).alt || leverLogo.textContent?.trim() || '';
      }
      if (!companyName && url.includes('lever.co/')) {
        const match = url.match(/lever\.co\/([^/?#]+)/);
        if (match && match[1]) {
          companyName = match[1].charAt(0).toUpperCase() + match[1].slice(1);
        }
      }
      const leverDesc = document.querySelector('.section.page-centered, .posting-page, [data-qa="job-description"]');
      if (leverDesc) {
        jobDescription = leverDesc.textContent?.trim().slice(0, 1500) || '';
      }

      // 2. Greenhouse-specific extraction
      if (!jobTitle) {
        const ghTitle = document.querySelector('.app-title, #app-title, .job-title');
        if (ghTitle) jobTitle = ghTitle.textContent?.trim() || '';
      }
      if (!companyName) {
        const ghCompany = document.querySelector('.company-name, .logo img');
        if (ghCompany) companyName = (ghCompany as HTMLImageElement).alt || ghCompany.textContent?.trim() || '';
      }
      if (!jobDescription) {
        const ghDesc = document.querySelector('#content, .content, #job-description');
        if (ghDesc) jobDescription = ghDesc.textContent?.trim().slice(0, 1500) || '';
      }

      // 3. Workday-specific extraction
      if (!jobTitle) {
        const wdTitle = document.querySelector('[data-automation-id="jobPostingHeader"]');
        if (wdTitle) jobTitle = wdTitle.textContent?.trim() || '';
      }

      // 4. Generic DOM extraction
      if (!jobTitle) {
        const h1 = document.querySelector('h1');
        if (h1 && h1.textContent) {
          jobTitle = h1.textContent.trim();
        }
      }

      // 5. Meta tags & Title heuristics
      if (!companyName) {
        const ogSiteName = document.querySelector('meta[property="og:site_name"]');
        if (ogSiteName) {
          companyName = ogSiteName.getAttribute('content')?.trim() || '';
        }
      }

      // 6. Title parsing (e.g. "Software Engineer at Paytm" or "Paytm - Careers")
      const docTitle = document.title.trim();
      if (!companyName && docTitle) {
        if (docTitle.includes(' at ')) {
          const parts = docTitle.split(' at ');
          companyName = parts[1].split(/[-–|]/)[0].trim();
          if (!jobTitle) jobTitle = parts[0].trim();
        } else if (docTitle.includes(' - ')) {
          const parts = docTitle.split(' - ');
          if (!jobTitle) jobTitle = parts[0].trim();
          companyName = parts[1].split(/[-–|]/)[0].trim();
        } else if (docTitle.includes(' | ')) {
          const parts = docTitle.split(' | ');
          if (!jobTitle) jobTitle = parts[0].trim();
          companyName = parts[1].trim();
        }
      }

      // 7. General description fallback
      if (!jobDescription) {
        const descEl = document.querySelector('.job-description, [class*="jobDescription"], [class*="description"], article, main');
        if (descEl) {
          jobDescription = descEl.textContent?.trim().slice(0, 1500) || '';
        }
      }
    } catch (e) {
      console.warn('[ApplyForMe] Context extraction note:', e);
    }

    return {
      companyName: companyName || '',
      jobTitle: jobTitle || '',
      jobDescription: jobDescription || '',
      url
    };
  }
}


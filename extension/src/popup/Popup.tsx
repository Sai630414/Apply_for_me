import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { storage } from '../lib/storage';
import { getGoogleIdToken } from '../lib/auth';
import { User, ApplicantProfile, AutofillResult, FormFieldDescriptor, FormFieldMapping, FormMappingResponse, ResumeMetadata } from '../lib/types';
import {
  Sparkles,
  CheckCircle,
  ExternalLink,
  ShieldCheck,
  UserCheck,
  AlertCircle,
  Play,
  Search,
  Settings,
  LogIn,
  LogOut,
  Loader2,
  Check,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  FileText,
  RefreshCw
} from 'lucide-react';

export const Popup: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<ApplicantProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [detecting, setDetecting] = useState<boolean>(false);
  const [autofilling, setAutofilling] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'info' | 'success' | 'error' | 'warning' } | null>(null);
  const [currentDomain, setCurrentDomain] = useState<string>('');
  const [avatarError, setAvatarError] = useState<boolean>(false);
  const [autofillResult, setAutofillResult] = useState<AutofillResult | null>(null);
  const [showFieldList, setShowFieldList] = useState<boolean>(false);
  const [progressStep, setProgressStep] = useState<string>('');
  const [aiMappings, setAiMappings] = useState<FormFieldMapping[]>([]);
  const [allMappings, setAllMappings] = useState<FormFieldMapping[]>([]);
  const [mappingStats, setMappingStats] = useState<FormMappingResponse | null>(null);
  const [resumes, setResumes] = useState<ResumeMetadata[]>([]);
  const [showAiReview, setShowAiReview] = useState<boolean>(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editedText, setEditedText] = useState<string>('');
  const [approvedIndices, setApprovedIndices] = useState<number[]>([]);

  useEffect(() => {
    loadUserData();
    fetchActiveTabAndScan();
  }, []);

  const fetchActiveTabAndScan = async () => {
    if (typeof chrome !== 'undefined' && chrome.tabs) {
      try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab?.url) {
          try {
            const url = new URL(tab.url);
            setCurrentDomain(url.hostname);
          } catch {
            setCurrentDomain('Web Application Page');
          }
        }
        // Automatically check for application form on current tab upon opening popup
        if (tab?.id && tab.url && !tab.url.startsWith('chrome://') && !tab.url.startsWith('chrome-extension://') && !tab.url.startsWith('edge://')) {
          chrome.tabs.sendMessage(tab.id, { action: 'DETECT_APPLICATION' }, (res) => {
            if (!chrome.runtime.lastError && res && res.fieldsCount > 0) {
              setStatusMessage({
                text: `Detected ${res.fieldsCount} input fields (${res.isJobForm ? 'Job application recognized' : 'General form'}).`,
                type: 'info'
              });
            }
          });
        }
      } catch (err) {
        console.debug('[ApplyForMe] Popup auto-detect note:', err);
      }
    } else {
      setCurrentDomain('localhost:5173 (Preview)');
    }
  };

  const loadUserData = async () => {
    setLoading(true);
    try {
      const cachedUser = await storage.get<User>('current_user');
      const token = await storage.get<string>('auth_token');
      if (cachedUser && token) {
        setUser(cachedUser);
        try {
          const p = await api.getProfile();
          setProfile(p);
        } catch (err) {
          console.warn('[ApplyForMe] Profile fetch error:', err);
        }
      }
    } catch (e) {
      console.error('[ApplyForMe] User load error:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setAuthLoading(true);
    setStatusMessage(null);
    try {
      const idToken = await getGoogleIdToken();
      const res = await api.googleLogin(idToken);
      setUser(res.user);
      setAvatarError(false);
      try {
        const p = await api.getProfile();
        setProfile(p);
      } catch {}
      setStatusMessage({ text: `Signed in as ${res.user.name}`, type: 'success' });
    } catch (err: any) {
      console.error('[ApplyForMe] Google Login Error:', err);
      setStatusMessage({ text: err.message || 'Google sign-in failed. Please try again.', type: 'error' });
    } finally {
      setAuthLoading(false);
    }
  };

  const handleDevLogin = async () => {
    setAuthLoading(true);
    setStatusMessage(null);
    try {
      const res = await api.devLogin('saikondareddypala@gmail.com', 'Sai Konda Reddy');
      setUser(res.user);
      setAvatarError(false);
      try {
        const p = await api.getProfile();
        setProfile(p);
      } catch {}
      setStatusMessage({ text: `Signed in as ${res.user.name}`, type: 'success' });
    } catch (err: any) {
      setStatusMessage({ text: `Login error: ${err.message}`, type: 'error' });
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    setLoading(true);
    try {
      await api.logout();
      setUser(null);
      setProfile(null);
      setAvatarError(false);
      setAutofillResult(null);
      setStatusMessage({ text: 'Signed out successfully.', type: 'info' });
    } catch (err: any) {
      setStatusMessage({ text: `Logout error: ${err.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  /**
   * Validate active tab and ensure content script is injected.
   */
  const getVerifiedActiveTab = async (): Promise<chrome.tabs.Tab> => {
    if (typeof chrome === 'undefined' || !chrome.tabs) {
      throw new Error('Chrome tabs API is unavailable in this environment.');
    }

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) {
      throw new Error('No active browser tab found.');
    }

    const url = tab.url || '';
    if (
      url.startsWith('chrome://') ||
      url.startsWith('chrome-extension://') ||
      url.startsWith('edge://') ||
      url.startsWith('about:') ||
      url.startsWith('devtools://') ||
      url.startsWith('view-source:')
    ) {
      throw new Error('ApplyForMe cannot run on internal browser pages. Please open a job application page.');
    }

    // Ping the tab to verify content script responsiveness
    const isAlive = await new Promise<boolean>((resolve) => {
      chrome.tabs.sendMessage(tab.id!, { action: 'PING' }, (res) => {
        if (chrome.runtime.lastError || !res) {
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });

    // If content script was not already present, inject it dynamically
    if (!isAlive && chrome.scripting) {
      try {
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ['src/content/content_script.js']
        });
        // Brief pause to allow initialization
        await new Promise((r) => setTimeout(r, 150));
      } catch (injErr: any) {
        throw new Error(`Could not access this webpage: ${injErr.message}`);
      }
    }

    return tab;
  };

  const handleDetectForm = async () => {
    setDetecting(true);
    setStatusMessage(null);
    setAutofillResult(null);

    try {
      const tab = await getVerifiedActiveTab();
      chrome.tabs.sendMessage(tab.id!, { action: 'DETECT_APPLICATION' }, (res) => {
        setDetecting(false);
        if (chrome.runtime.lastError) {
          setStatusMessage({ text: 'Please refresh the job application page and try again.', type: 'error' });
        } else if (res?.fieldsCount > 0) {
          setStatusMessage({
            text: `Detected ${res.fieldsCount} input fields (${res.isJobForm ? 'Job application recognized' : 'General form'}).`,
            type: 'success'
          });
        } else {
          setStatusMessage({ text: 'No fillable fields detected on this page.', type: 'info' });
        }
      });
    } catch (err: any) {
      setDetecting(false);
      setStatusMessage({ text: err.message || 'Detection failed.', type: 'error' });
    }
  };

  const handleStartAutofill = async () => {
    if (!user) {
      setStatusMessage({ text: 'Please sign in to your ApplyForMe account first.', type: 'warning' });
      return;
    }

    setAutofilling(true);
    setStatusMessage(null);
    setAutofillResult(null);

    try {
      const tab = await getVerifiedActiveTab();

      // 1. Stage 1: Detect fields
      setProgressStep('1/6 Detecting application form fields...');
      const detectResponse: { isJobForm: boolean; fieldsCount: number; fields: FormFieldDescriptor[]; jobContext?: any } =
        await new Promise((resolve, reject) => {
          chrome.tabs.sendMessage(tab.id!, { action: 'DETECT_APPLICATION' }, (res) => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else {
              resolve(res);
            }
          });
        });

      if (!detectResponse || !detectResponse.fields || detectResponse.fields.length === 0) {
        setAutofilling(false);
        setProgressStep('');
        setStatusMessage({
          text: 'No input fields detected on this page. Please open an application form.',
          type: 'warning'
        });
        return;
      }

      // 2. Stage 2: Retrieve applicant profile
      setProgressStep('2/6 Retrieving applicant profile credentials...');
      await new Promise(r => setTimeout(r, 150));

      // 3. Stage 3 & 4: Classifying and generating AI answers with Groq
      setProgressStep('3/6 Classifying fields & 4/6 Generating AI answers with Groq...');
      let mappingResponse: FormMappingResponse;
      try {
        const jobCtx = detectResponse.jobContext || {};
        mappingResponse = await api.mapFormFields({
          fields: detectResponse.fields,
          companyName: jobCtx.companyName || '',
          jobTitle: jobCtx.jobTitle || '',
          jobDescription: jobCtx.jobDescription || '',
          url: jobCtx.url || tab.url || ''
        });
      } catch (apiErr: any) {
        setAutofilling(false);
        setProgressStep('');
        setStatusMessage({
          text: `Backend mapping error: ${apiErr.message}. Ensure the FastAPI server is running.`,
          type: 'error'
        });
        return;
      }

      if (!mappingResponse || !mappingResponse.mappings || mappingResponse.mappings.length === 0) {
        setAutofilling(false);
        setProgressStep('');
        setStatusMessage({
          text: 'No fields could be matched or classified.',
          type: 'warning'
        });
        return;
      }

      setMappingStats(mappingResponse);
      setAllMappings(mappingResponse.mappings);

      // Fetch resumes if file upload fields are present
      if (mappingResponse.fileUploadCount && mappingResponse.fileUploadCount > 0) {
        try {
          const userResumes = await api.getResumes();
          setResumes(userResumes || []);
        } catch {}
      }

      // Store question & confirmation mappings for review/edit
      const questionItems = mappingResponse.mappings.filter(
        m => m.category === 'AI_GENERATED_ANSWER' ||
             m.category === 'USER_CONFIRMATION_REQUIRED' ||
             m.category === 'USER_INPUT_REQUIRED' ||
             m.requires_confirmation ||
             m.requiresReview ||
             Boolean(m.questionCategory)
      );
      setAiMappings(questionItems);

      // 4. Stage 5: Filling verified form fields into DOM
      setProgressStep('5/6 Populating verified form fields into DOM...');
      await new Promise(r => setTimeout(r, 150));

      // 5. Stage 6: Verifying live DOM results
      setProgressStep('6/6 Verifying live DOM element values...');

      chrome.tabs.sendMessage(
        tab.id!,
        { action: 'START_AUTOFILL', mappings: mappingResponse.mappings },
        (result: AutofillResult) => {
          setAutofilling(false);
          setProgressStep('');

          if (chrome.runtime.lastError) {
            setStatusMessage({
              text: `Autofill communication error: ${chrome.runtime.lastError.message}`,
              type: 'error'
            });
            return;
          }

          if (!result) {
            setStatusMessage({
              text: 'Content script did not return a verification response.',
              type: 'error'
            });
            return;
          }

          setAutofillResult(result);
          setShowFieldList(true);

          if (result.totalFilled > 0) {
            setStatusMessage({
              text: `Success! Filled ${result.totalFilled} fields (${result.directMappedCount || 0} profile, ${result.aiGeneratedCount || 0} AI generated).`,
              type: 'success'
            });
          } else {
            setStatusMessage({
              text: 'No fields were filled. Please check the detected fields and your applicant profile.',
              type: 'warning'
            });
          }
        }
      );
    } catch (err: any) {
      setAutofilling(false);
      setProgressStep('');
      setStatusMessage({ text: err.message || 'Autofill pipeline error.', type: 'error' });
    }
  };

  const handleApplyEditedAnswer = async (idx: number) => {
    try {
      const tab = await getVerifiedActiveTab();
      const updatedAiMappings = [...aiMappings];
      updatedAiMappings[idx].fillValue = editedText;
      updatedAiMappings[idx].proposed_answer = editedText;
      updatedAiMappings[idx].requiresReview = false;
      updatedAiMappings[idx].requires_confirmation = false;
      setAiMappings(updatedAiMappings);
      setEditingIndex(null);
      if (!approvedIndices.includes(idx)) {
        setApprovedIndices((prev) => [...prev, idx]);
      }

      // Re-fill this specific field into the webpage
      chrome.tabs.sendMessage(
        tab.id!,
        { action: 'START_AUTOFILL', mappings: [updatedAiMappings[idx]] },
        (res: AutofillResult) => {
          if (res && res.totalFilled > 0) {
            setStatusMessage({ text: `Approved & filled: '${updatedAiMappings[idx].fieldName}'`, type: 'success' });
          } else {
            setStatusMessage({ text: `Updated answer applied to '${updatedAiMappings[idx].fieldName}'`, type: 'info' });
          }
        }
      );
    } catch (e: any) {
      setStatusMessage({ text: `Failed to apply edit: ${e.message}`, type: 'error' });
    }
  };

  const handleApproveAnswer = async (idx: number) => {
    try {
      const tab = await getVerifiedActiveTab();
      const target = { ...aiMappings[idx] };
      const valToFill = target.fillValue || target.proposed_answer;
      if (!valToFill) return;

      target.fillValue = valToFill;
      target.requiresReview = false;
      target.requires_confirmation = false;

      if (!approvedIndices.includes(idx)) {
        setApprovedIndices((prev) => [...prev, idx]);
      }

      chrome.tabs.sendMessage(
        tab.id!,
        { action: 'START_AUTOFILL', mappings: [target] },
        (res: AutofillResult) => {
          if (res && res.totalFilled > 0) {
            setStatusMessage({ text: `Confirmed & populated: '${target.fieldName}'`, type: 'success' });
          } else {
            setStatusMessage({ text: `Applied: '${target.fieldName}'`, type: 'info' });
          }
        }
      );
    } catch (e: any) {
      setStatusMessage({ text: `Failed to approve: ${e.message}`, type: 'error' });
    }
  };

  const handleFillAllConfirmed = async () => {
    try {
      const tab = await getVerifiedActiveTab();
      const confirmedMappings = aiMappings
        .filter((m, idx) => (approvedIndices.includes(idx) || m.category === 'AI_GENERATED_ANSWER') && Boolean(m.fillValue || m.proposed_answer))
        .map(m => ({
          ...m,
          fillValue: m.fillValue || m.proposed_answer,
          requiresReview: false,
          requires_confirmation: false
        }));

      if (confirmedMappings.length === 0) {
        setStatusMessage({ text: 'No approved fields ready to fill.', type: 'info' });
        return;
      }

      chrome.tabs.sendMessage(
        tab.id!,
        { action: 'START_AUTOFILL', mappings: confirmedMappings },
        (res: AutofillResult) => {
          if (res && res.totalFilled > 0) {
            setStatusMessage({ text: `Filled ${res.totalFilled} confirmed fields!`, type: 'success' });
            setAutofillResult(res);
          }
        }
      );
    } catch (e: any) {
      setStatusMessage({ text: `Fill error: ${e.message}`, type: 'error' });
    }
  };

  const handleRetryFailed = async () => {
    if (!autofillResult || !autofillResult.fields) return;
    const failedIds = new Set(autofillResult.fields.filter(f => f.status === 'failed').map(f => f.elementIdentifier));
    const failedMappings = allMappings.filter(m => failedIds.has(m.elementIdentifier));
    if (failedMappings.length === 0) {
      setStatusMessage({ text: 'No failed fields to retry.', type: 'info' });
      return;
    }
    try {
      const tab = await getVerifiedActiveTab();
      chrome.tabs.sendMessage(
        tab.id!,
        { action: 'START_AUTOFILL', mappings: failedMappings },
        (res: AutofillResult) => {
          if (res) {
            setStatusMessage({ text: `Retry: ${res.totalFilled} filled, ${res.failed} remaining failed.`, type: res.totalFilled > 0 ? 'success' : 'warning' });
            setAutofillResult(res);
          }
        }
      );
    } catch (e: any) {
      setStatusMessage({ text: `Retry error: ${e.message}`, type: 'error' });
    }
  };

  const openDashboard = () => {
    if (typeof chrome !== 'undefined' && chrome.tabs) {
      chrome.tabs.create({ url: chrome.runtime.getURL('dashboard.html') });
    } else {
      window.open('/dashboard.html', '_blank');
    }
  };

  return (
    <div style={{ width: 380, padding: 16, background: '#f8fafc', boxSizing: 'border-box', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: 16,
              boxShadow: '0 2px 4px rgba(79, 70, 229, 0.25)'
            }}
          >
            <Sparkles size={18} />
          </div>
          <div>
            <h1 style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', margin: 0, lineHeight: 1.2 }}>ApplyForMe</h1>
            <p style={{ fontSize: 11, color: '#64748b', margin: 0 }}>One Profile. Smarter Applications.</p>
          </div>
        </div>

        <button
          onClick={openDashboard}
          title="Open Dashboard"
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', padding: 4 }}
        >
          <Settings size={18} />
        </button>
      </div>

      {/* Authentication Card */}
      {loading ? (
        <div style={{ padding: 20, marginBottom: 14, background: '#fff', textAlign: 'center', borderRadius: 10, border: '1px solid #e2e8f0' }}>
          <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', margin: '0 auto 8px', color: '#4f46e5' }} />
          <span style={{ fontSize: 12, color: '#64748b' }}>Checking user session...</span>
        </div>
      ) : !user ? (
        <div style={{ padding: 16, marginBottom: 14, background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <AlertCircle size={16} color="#4f46e5" />
            <span style={{ fontSize: 13, fontWeight: 600, color: '#0f172a' }}>Sign in to ApplyForMe</span>
          </div>
          <p style={{ fontSize: 12, color: '#64748b', marginBottom: 14, lineHeight: 1.4 }}>
            Sign in with your Google account to access your centralized profile and enable smart form filling.
          </p>

          <button
            onClick={handleGoogleLogin}
            disabled={authLoading}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              padding: '10px 14px',
              backgroundColor: '#4f46e5',
              color: '#ffffff',
              border: 'none',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: authLoading ? 'not-allowed' : 'pointer',
              marginBottom: 8
            }}
          >
            <LogIn size={15} /> {authLoading ? 'Signing in...' : 'Sign in with Google'}
          </button>

          <button
            onClick={handleDevLogin}
            disabled={authLoading}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              padding: '8px 12px',
              backgroundColor: '#f1f5f9',
              color: '#475569',
              border: '1px solid #e2e8f0',
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 500,
              cursor: authLoading ? 'not-allowed' : 'pointer'
            }}
          >
            Quick Demo Sign In (saikondareddypala@gmail.com)
          </button>
        </div>
      ) : (
        /* Authenticated User Card */
        <div style={{ padding: 14, marginBottom: 14, background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {user.picture && !avatarError ? (
                <img
                  src={user.picture}
                  alt={user.name}
                  onError={() => setAvatarError(true)}
                  style={{ width: 32, height: 32, borderRadius: '50%', objectFit: 'cover', border: '1px solid #e2e8f0' }}
                />
              ) : (
                <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#e0e7ff', color: '#4f46e5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: 13 }}>
                  {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
                </div>
              )}

              <div style={{ maxWidth: 200 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {user.name}
                </div>
                <div style={{ fontSize: 11, color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {user.email}
                </div>
              </div>
            </div>

            <button
              onClick={handleLogout}
              title="Sign Out"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                background: '#fef2f2',
                color: '#b91c1c',
                border: '1px solid #fecaca',
                borderRadius: 6,
                padding: '4px 8px',
                fontSize: 11,
                fontWeight: 500,
                cursor: 'pointer'
              }}
            >
              <LogOut size={12} />
              <span>Logout</span>
            </button>
          </div>

          {/* Profile Strength Bar */}
          <div style={{ paddingTop: 8, borderTop: '1px solid #f1f5f9' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ color: '#475569', fontWeight: 500 }}>Profile Strength</span>
              <span style={{ fontWeight: 600, color: '#4f46e5' }}>
                {profile?.completionPercentage || 0}%
              </span>
            </div>
            <div style={{ height: 6, background: '#f1f5f9', borderRadius: 3, overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  background: 'linear-gradient(90deg, #4f46e5 0%, #6366f1 100%)',
                  width: `${profile?.completionPercentage || 0}%`,
                  transition: 'width 0.3s ease'
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Website Domain Info */}
      <div
        style={{
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: 8,
          padding: '8px 12px',
          marginBottom: 12,
          fontSize: 12,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}
      >
        <span style={{ color: '#64748b' }}>Active Portal:</span>
        <span style={{ fontWeight: 600, color: '#0f172a', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {currentDomain || 'Detecting...'}
        </span>
      </div>

      {/* Primary Actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
        <button
          onClick={handleStartAutofill}
          disabled={!user || autofilling}
          style={{
            width: '100%',
            padding: 10,
            fontSize: 13,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            backgroundColor: '#4f46e5',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            cursor: !user || autofilling ? 'not-allowed' : 'pointer',
            opacity: !user ? 0.6 : 1
          }}
        >
          {autofilling ? (
            <>
              <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />
              <span>Autofilling with AI...</span>
            </>
          ) : (
            <>
              <Sparkles size={15} />
              <span>Autofill Application Form</span>
            </>
          )}
        </button>

        <button
          onClick={handleDetectForm}
          disabled={detecting || autofilling}
          style={{
            width: '100%',
            padding: 8,
            fontSize: 12,
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            background: '#fff',
            color: '#334155',
            border: '1px solid #cbd5e1',
            borderRadius: 8,
            cursor: detecting || autofilling ? 'not-allowed' : 'pointer'
          }}
        >
          <Search size={14} /> {detecting ? 'Scanning Webpage...' : 'Scan Form Fields'}
        </button>
      </div>

      {/* Progress Stage Step */}
      {progressStep && (
        <div style={{ padding: '8px 12px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#1d4ed8' }}>
          <Loader2 size={13} style={{ animation: 'spin 1s linear infinite', flexShrink: 0 }} />
          <span style={{ fontWeight: 500 }}>{progressStep}</span>
        </div>
      )}

      {/* Status Notice */}
      {statusMessage && !progressStep && (
        <div
          style={{
            padding: '9px 12px',
            background:
              statusMessage.type === 'error'
                ? '#fef2f2'
                : statusMessage.type === 'success'
                ? '#f0fdf4'
                : statusMessage.type === 'warning'
                ? '#fffbeb'
                : '#eff6ff',
            border: `1px solid ${
              statusMessage.type === 'error'
                ? '#fecaca'
                : statusMessage.type === 'success'
                ? '#bbf7d0'
                : statusMessage.type === 'warning'
                ? '#fde68a'
                : '#bfdbfe'
            }`,
            borderRadius: 8,
            fontSize: 12,
            color:
              statusMessage.type === 'error'
                ? '#b91c1c'
                : statusMessage.type === 'success'
                ? '#15803d'
                : statusMessage.type === 'warning'
                ? '#b45309'
                : '#1e40af',
            marginBottom: 12,
            textAlign: 'center',
            lineHeight: 1.4
          }}
        >
          {statusMessage.text}
        </div>
      )}

      {/* Application Questions & AI Review Card */}
      {aiMappings.length > 0 && (
        <div style={{ background: '#f5f3ff', border: '1px solid #ddd6fe', borderRadius: 8, padding: 12, marginBottom: 12, fontSize: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: showAiReview ? 8 : 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Sparkles size={14} color="#7c3aed" />
              <span style={{ fontWeight: 600, color: '#5b21b6' }}>Application Questions & AI Answers ({aiMappings.length})</span>
            </div>
            <button
              onClick={() => setShowAiReview(!showAiReview)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6d28d9', fontSize: 11, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 2 }}
            >
              {showAiReview ? 'Hide' : 'Review / Edit'} {showAiReview ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>

          {showAiReview && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
              {aiMappings.map((m, idx) => {
                const isNeedsInput = !m.fillValue || m.category === 'USER_INPUT_REQUIRED' || m.status === 'needs_user_input';
                const isVerifiedProfile = !isNeedsInput && (m.questionCategory === 'PRIOR_EXPERIENCE' || m.reason?.toLowerCase().includes('verified'));
                const isApproved = approvedIndices.includes(idx);

                return (
                  <div key={idx} style={{ background: '#ffffff', border: `1px solid ${isNeedsInput ? '#fde68a' : '#ede9fe'}`, borderRadius: 6, padding: 9 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 6, marginBottom: 5 }}>
                      <div style={{ fontWeight: 600, color: '#1e293b', fontSize: 11, lineHeight: 1.3 }}>
                        <span style={{ color: '#64748b', fontWeight: 500, marginRight: 4 }}>Question:</span>
                        {m.fieldName || 'Application Question'}
                      </div>
                      <div style={{ flexShrink: 0 }}>
                        {isNeedsInput ? (
                          <span style={{ background: '#fef3c7', color: '#b45309', padding: '2px 6px', borderRadius: 4, fontSize: 10, fontWeight: 600, whiteSpace: 'nowrap' }}>
                            Needs your input
                          </span>
                        ) : isVerifiedProfile ? (
                          <span style={{ background: '#f0fdf4', color: '#15803d', padding: '2px 6px', borderRadius: 4, fontSize: 10, fontWeight: 600, whiteSpace: 'nowrap' }}>
                            Generated from verified profile
                          </span>
                        ) : (
                          <span style={{ background: '#ede9fe', color: '#6d28d9', padding: '2px 6px', borderRadius: 4, fontSize: 10, fontWeight: 600, whiteSpace: 'nowrap' }}>
                            AI answer ready
                          </span>
                        )}
                      </div>
                    </div>

                    {editingIndex === idx ? (
                      <div>
                        <textarea
                          value={editedText}
                          onChange={(e) => setEditedText(e.target.value)}
                          placeholder="Type or edit your answer..."
                          style={{ width: '100%', minHeight: 65, fontSize: 11, padding: 6, border: '1px solid #c4b5fd', borderRadius: 4, fontFamily: 'inherit', resize: 'vertical', boxSizing: 'border-box' }}
                        />
                        <div style={{ display: 'flex', gap: 6, marginTop: 6, justifyContent: 'flex-end' }}>
                          <button
                            onClick={() => setEditingIndex(null)}
                            style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: 4, padding: '3px 8px', fontSize: 11, cursor: 'pointer' }}
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleApplyEditedAnswer(idx)}
                            style={{ background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 4, padding: '3px 10px', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}
                          >
                            Approve & Fill
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        {m.fillValue || m.proposed_answer ? (
                          <div style={{ color: isNeedsInput ? '#92400e' : '#334155', fontSize: 11, lineHeight: 1.4, maxHeight: 75, overflowY: 'auto' }}>
                            {isNeedsInput && (
                              <div style={{ fontSize: 10, color: '#b45309', fontWeight: 600, marginBottom: 2 }}>
                                Proposed Answer (Requires Confirmation):
                              </div>
                            )}
                            <div>{m.fillValue || m.proposed_answer}</div>
                            {m.confirmation_reason && (
                              <div style={{ fontSize: 10, color: '#64748b', marginTop: 3 }}>
                                Note: {m.confirmation_reason}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div style={{ color: '#b45309', fontSize: 11, fontStyle: 'italic' }}>
                            Personal input required — ApplyForMe will not autofill this field without your explicit confirmation.
                          </div>
                        )}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6, paddingTop: 4, borderTop: '1px solid #f1f5f9' }}>
                          <span style={{ fontSize: 10, color: '#8b5cf6' }}>
                            {m.questionCategory ? `Category: ${m.questionCategory}` : `Confidence: ${Math.round((m.confidence || 0.9) * 100)}%`}
                          </span>
                          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                            <button
                              onClick={() => {
                                setEditingIndex(idx);
                                setEditedText(m.fillValue || m.proposed_answer || '');
                              }}
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#7c3aed', fontSize: 11, fontWeight: 500 }}
                            >
                              {isNeedsInput ? 'Edit Proposal' : 'Edit'}
                            </button>
                            {(m.fillValue || m.proposed_answer) && (
                              <button
                                onClick={() => handleApproveAnswer(idx)}
                                style={{
                                  background: isApproved ? '#dcfce7' : '#7c3aed',
                                  color: isApproved ? '#15803d' : '#fff',
                                  border: isApproved ? '1px solid #86efac' : 'none',
                                  borderRadius: 4,
                                  padding: '2px 8px',
                                  fontSize: 10,
                                  fontWeight: 600,
                                  cursor: 'pointer'
                                }}
                              >
                                {isApproved ? '✓ Filled' : 'Approve & Fill'}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Action to fill all approved / AI answers */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8, paddingTop: 8, borderTop: '1px solid #ddd6fe' }}>
                <button
                  onClick={handleFillAllConfirmed}
                  style={{
                    background: '#7c3aed',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 6,
                    padding: '6px 12px',
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5
                  }}
                >
                  <Sparkles size={12} /> Fill All Confirmed Answers
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Resume Selection Helper when file uploads detected */}
      {resumes.length > 0 && (
        <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, padding: 12, marginBottom: 12, fontSize: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <FileText size={14} color="#2563eb" />
            <span style={{ fontWeight: 600, color: '#1e40af' }}>Applicant Resumes ({resumes.length})</span>
          </div>
          <p style={{ fontSize: 11, color: '#475569', margin: '0 0 8px 0', lineHeight: 1.3 }}>
            Due to browser security policies, file inputs cannot be filled automatically. Please click the file upload field on the webpage and select one of your profile resumes:
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {resumes.map((r, rIdx) => (
              <div key={rIdx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#fff', padding: '6px 8px', borderRadius: 6, border: '1px solid #dbeafe', fontSize: 11 }}>
                <span style={{ fontWeight: 500, color: '#1e293b', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.title || r.fileName}
                </span>
                <span style={{ fontSize: 10, color: '#2563eb', fontWeight: 600 }}>
                  {r.isDefault ? '★ Default' : 'PDF'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Verified Autofill Results Breakdown Card */}
      {autofillResult && (
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 12, marginBottom: 12, fontSize: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontWeight: 600, color: '#0f172a' }}>Autofill Summary</span>
            <button
              onClick={() => setShowFieldList(!showFieldList)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#4f46e5', display: 'flex', alignItems: 'center', gap: 2, fontSize: 11, fontWeight: 500 }}
            >
              {showFieldList ? 'Hide details' : 'Show details'} {showFieldList ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 4, textAlign: 'center', marginBottom: 10 }}>
            <div style={{ background: '#f8fafc', padding: '6px 2px', borderRadius: 6, border: '1px solid #f1f5f9' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a' }}>{autofillResult.totalDetected}</div>
              <div style={{ fontSize: 9, color: '#64748b' }}>Detected</div>
            </div>
            <div style={{ background: '#f0fdf4', padding: '6px 2px', borderRadius: 6, border: '1px solid #dcfce7' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#16a34a' }}>{autofillResult.totalFilled}</div>
              <div style={{ fontSize: 9, color: '#15803d' }}>Filled</div>
            </div>
            <div style={{ background: '#ecfdf5', padding: '6px 2px', borderRadius: 6, border: '1px solid #a7f3d0' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#047857' }}>{autofillResult.directMappedCount || 0}</div>
              <div style={{ fontSize: 9, color: '#047857' }}>Profile</div>
            </div>
            <div style={{ background: '#f5f3ff', padding: '6px 2px', borderRadius: 6, border: '1px solid #ddd6fe' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#7c3aed' }}>{autofillResult.aiGeneratedCount || 0}</div>
              <div style={{ fontSize: 9, color: '#6d28d9' }}>AI Gen</div>
            </div>
            <div style={{ background: '#fffbeb', padding: '6px 2px', borderRadius: 6, border: '1px solid #fef3c7' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#d97706' }}>{autofillResult.skipped}</div>
              <div style={{ fontSize: 9, color: '#b45309' }}>Skipped</div>
            </div>
          </div>

          {/* Detailed Field List with Category Badges */}
          {showFieldList && (
            <div style={{ maxHeight: 200, overflowY: 'auto', borderTop: '1px solid #f1f5f9', paddingTop: 8 }}>
              {autofillResult.fields.map((f, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #f8fafc', fontSize: 11 }}>
                  <div style={{ maxWidth: 190, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span style={{ fontWeight: 500, color: '#334155' }}>{f.name}</span>
                    {f.reason && <span style={{ color: '#94a3b8', marginLeft: 4 }}>({f.reason})</span>}
                  </div>
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    {f.category === 'AI_GENERATED_ANSWER' && (
                      <span style={{ background: '#f5f3ff', color: '#7c3aed', border: '1px solid #ddd6fe', borderRadius: 4, padding: '1px 5px', fontSize: 9, fontWeight: 600 }}>
                        ✨ AI
                      </span>
                    )}
                    {f.category === 'DIRECT_PROFILE_FIELD' && (
                      <span style={{ background: '#f0fdf4', color: '#16a34a', border: '1px solid #bbf7d0', borderRadius: 4, padding: '1px 5px', fontSize: 9, fontWeight: 600 }}>
                        Profile
                      </span>
                    )}
                    {f.category === 'USER_INPUT_REQUIRED' && (
                      <span style={{ background: '#fffbeb', color: '#d97706', border: '1px solid #fef3c7', borderRadius: 4, padding: '1px 5px', fontSize: 9, fontWeight: 600 }}>
                        Needs Input
                      </span>
                    )}
                    {f.category === 'FILE_UPLOAD' && (
                      <span style={{ background: '#eff6ff', color: '#2563eb', border: '1px solid #bfdbfe', borderRadius: 4, padding: '1px 5px', fontSize: 9, fontWeight: 600 }}>
                        File
                      </span>
                    )}
                    {f.category === 'CONSENT_OR_LEGAL' && (
                      <span style={{ background: '#f1f5f9', color: '#64748b', border: '1px solid #cbd5e1', borderRadius: 4, padding: '1px 5px', fontSize: 9, fontWeight: 600 }}>
                        Legal
                      </span>
                    )}
                    {f.status === 'filled' && (
                      <span style={{ background: '#ecfdf5', color: '#047857', border: '1px solid #a7f3d0', borderRadius: 4, padding: '2px 5px', fontSize: 10, fontWeight: 600 }}>
                        Filled
                      </span>
                    )}
                    {f.status === 'skipped' && (
                      <span style={{ background: '#fef3c7', color: '#92400e', border: '1px solid #fde68a', borderRadius: 4, padding: '2px 5px', fontSize: 10, fontWeight: 600 }}>
                        Skipped
                      </span>
                    )}
                    {f.status === 'failed' && (
                      <span style={{ background: '#fee2e2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: 4, padding: '2px 5px', fontSize: 10, fontWeight: 600 }}>
                        Failed
                      </span>
                    )}
                  </div>
                </div>
              ))}
              {autofillResult.failed > 0 && (
                <div style={{ marginTop: 8, textAlign: 'center' }}>
                  <button
                    onClick={handleRetryFailed}
                    style={{
                      background: '#fee2e2',
                      color: '#991b1b',
                      border: '1px solid #fecaca',
                      borderRadius: 6,
                      padding: '4px 10px',
                      fontSize: 11,
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4
                    }}
                  >
                    <RefreshCw size={11} /> Retry {autofillResult.failed} Failed Fields
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Open Dashboard Link */}
      <button
        onClick={openDashboard}
        style={{
          width: '100%',
          padding: '8px 12px',
          background: '#ffffff',
          color: '#475569',
          border: '1px solid #cbd5e1',
          borderRadius: 8,
          fontSize: 12,
          fontWeight: 500,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 6
        }}
      >
        <ExternalLink size={13} /> Open Profile & Dashboard
      </button>

      {/* Footer */}
      <div style={{ marginTop: 14, textAlign: 'center', fontSize: 11, color: '#94a3b8' }}>
        ApplyForMe &bull; One Profile. Smarter Applications.
      </div>
    </div>
  );
};

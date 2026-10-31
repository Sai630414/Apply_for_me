import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { storage } from '../lib/storage';
import { getGoogleIdToken } from '../lib/auth';
import {
  User,
  ApplicantProfile,
  ApplicationRecord,
  ResumeMetadata,
  ProfileCompletionDetails,
  EducationItem,
  ExperienceItem,
  ProjectItem
} from '../lib/types';
import { OnboardingWizard } from './OnboardingWizard';
import {
  Sparkles,
  UserCheck,
  Briefcase,
  FileText,
  Save,
  CheckCircle,
  AlertCircle,
  LogOut,
  GraduationCap,
  Code,
  FolderGit2,
  Globe,
  Settings,
  TrendingUp,
  Cpu,
  Plus,
  Trash2,
  UploadCloud,
  Check,
  ExternalLink,
  ChevronRight,
  RefreshCw,
  Compass,
  Star
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<ApplicantProfile | null>(null);
  const [completion, setCompletion] = useState<ProfileCompletionDetails | null>(null);
  const [resumes, setResumes] = useState<ResumeMetadata[]>([]);
  const [applications, setApplications] = useState<ApplicationRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [showWizard, setShowWizard] = useState<boolean>(false);
  const [avatarError, setAvatarError] = useState<boolean>(false);

  // Active navigation tab
  const [activeTab, setActiveTab] = useState<
    'overview' | 'personal' | 'education' | 'skills' | 'experience' | 'resumes' | 'career' | 'applications' | 'settings'
  >('overview');

  // Status feedback toast
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Resume upload form state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState<string>('My Resume');
  const [uploadCategory, setUploadCategory] = useState<string>('General');
  const [isUploading, setIsUploading] = useState<boolean>(false);

  // Skills tag input
  const [newSkillTag, setNewSkillTag] = useState<{ [category: string]: string }>({});

  useEffect(() => {
    loadInitialData();
  }, []);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 4000);
  };

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const cachedUser = await storage.get<User>('current_user');
      const token = await storage.get<string>('auth_token');

      if (cachedUser && token) {
        setUser(cachedUser);
        await refreshUserData();
      }
    } catch (err) {
      console.warn('Dashboard initial load:', err);
    } finally {
      setLoading(false);
    }
  };

  const refreshUserData = async () => {
    try {
      // 1. Fetch profile
      try {
        const prof = await api.getProfile();
        setProfile(prof);
        if (!prof.onboardingCompleted) {
          setShowWizard(true);
        }
      } catch (e) {
        console.warn('Profile fetch:', e);
      }

      // 2. Fetch completion score
      try {
        const comp = await api.getProfileCompletion();
        setCompletion(comp);
      } catch (e) {
        console.warn('Completion fetch:', e);
      }

      // 3. Fetch resumes
      try {
        const resList = await api.getResumes();
        setResumes(resList || []);
      } catch (e) {
        console.warn('Resumes fetch:', e);
      }

      // 4. Fetch applications
      try {
        const apps = await api.getApplications();
        setApplications(apps || []);
      } catch (e) {
        console.warn('Applications fetch:', e);
      }
    } catch (err) {
      console.error('Refresh error:', err);
    }
  };

  // Google OAuth Login
  const handleGoogleLogin = async () => {
    setAuthLoading(true);
    try {
      const idToken = await getGoogleIdToken();
      const res = await api.googleLogin(idToken);
      setUser(res.user);
      setAvatarError(false);
      await refreshUserData();
      showToast(`Welcome back, ${res.user.name}!`);
    } catch (err: any) {
      showToast(err.message || 'Google sign-in failed', 'error');
    } finally {
      setAuthLoading(false);
    }
  };

  // Dev Quick Login for local testing
  const handleDevLogin = async () => {
    setAuthLoading(true);
    try {
      const res = await api.devLogin('saikondareddypala@gmail.com', 'Sai Konda Reddy');
      setUser(res.user);
      setAvatarError(false);
      await refreshUserData();
      showToast(`Signed in as ${res.user.name}`);
    } catch (err: any) {
      showToast(err.message || 'Login failed', 'error');
    } finally {
      setAuthLoading(false);
    }
  };

  // Logout
  const handleLogout = async () => {
    try {
      await api.logout();
      setUser(null);
      setProfile(null);
      setCompletion(null);
      setResumes([]);
      setApplications([]);
      setShowWizard(false);
      showToast('Successfully logged out.');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  // Save full profile update
  const handleSaveProfile = async () => {
    if (!profile) return;
    setSaving(true);
    try {
      const updated = await api.updateProfile(profile);
      setProfile(updated);
      const comp = await api.getProfileCompletion();
      setCompletion(comp);
      showToast('Profile saved successfully!');
    } catch (err: any) {
      showToast(err.message || 'Failed to update profile', 'error');
    } finally {
      setSaving(false);
    }
  };

  // Resume Upload Handler
  const handleResumeUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      showToast('Please select a PDF file to upload', 'error');
      return;
    }
    if (!uploadFile.name.toLowerCase().endsWith('.pdf')) {
      showToast('Only PDF files are supported', 'error');
      return;
    }
    if (uploadFile.size > 5 * 1024 * 1024) {
      showToast('File size must be 5MB or less', 'error');
      return;
    }

    setIsUploading(true);
    try {
      const isFirst = resumes.length === 0;
      await api.uploadResume(uploadFile, uploadTitle, uploadCategory, isFirst);
      setUploadFile(null);
      setUploadTitle('My Resume');
      const updatedResumes = await api.getResumes();
      setResumes(updatedResumes);
      showToast('Resume uploaded successfully!');
    } catch (err: any) {
      showToast(err.message || 'Failed to upload resume', 'error');
    } finally {
      setIsUploading(false);
    }
  };

  // Toggle Default Resume
  const handleSetDefaultResume = async (resumeId: string) => {
    try {
      await api.setDefaultResume(resumeId);
      const updated = await api.getResumes();
      setResumes(updated);
      showToast('Default resume updated.');
    } catch (err: any) {
      showToast(err.message || 'Failed to set default', 'error');
    }
  };

  // Delete Resume
  const handleDeleteResume = async (resumeId: string) => {
    if (!confirm('Are you sure you want to delete this resume?')) return;
    try {
      await api.deleteResume(resumeId);
      setResumes(resumes.filter((r) => r._id !== resumeId));
      showToast('Resume deleted.');
    } catch (err: any) {
      showToast(err.message || 'Failed to delete resume', 'error');
    }
  };

  // Skills Tag helpers
  const handleAddSkillTag = (category: keyof ApplicantProfile['skills']) => {
    if (!profile) return;
    const val = (newSkillTag[category] || '').trim();
    if (!val) return;
    const currentList = (profile.skills[category] as string[]) || [];
    if (!currentList.includes(val)) {
      setProfile({
        ...profile,
        skills: {
          ...profile.skills,
          [category]: [...currentList, val]
        }
      });
    }
    setNewSkillTag({ ...newSkillTag, [category]: '' });
  };

  const handleRemoveSkillTag = (category: keyof ApplicantProfile['skills'], tag: string) => {
    if (!profile) return;
    const currentList = (profile.skills[category] as string[]) || [];
    setProfile({
      ...profile,
      skills: {
        ...profile.skills,
        [category]: currentList.filter((item) => item !== tag)
      }
    });
  };

  // Loading spinner during initial app load
  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '80vh', gap: 16 }}>
        <div className="stat-icon-wrap stat-icon-primary" style={{ animation: 'spin 1s linear infinite' }}>
          <RefreshCw size={24} />
        </div>
        <div style={{ fontSize: 14, color: '#64748b', fontWeight: 500 }}>Loading ApplyForMe...</div>
      </div>
    );
  }

  // Unauthenticated Sign-In View
  if (!user) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f8fafc', padding: 20 }}>
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 16, padding: '40px 32px', maxWidth: 440, width: '100%', textAlign: 'center', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.08)' }}>
          <div style={{ width: 48, height: 48, borderRadius: 12, background: 'linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', margin: '0 auto 16px', boxShadow: '0 4px 12px rgba(79, 70, 229, 0.3)' }}>
            <Sparkles size={26} />
          </div>

          <h2 style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', marginBottom: 6 }}>ApplyForMe</h2>
          <p style={{ fontSize: 13, color: '#64748b', marginBottom: 28 }}>One Profile. Smarter Applications.</p>

          <div style={{ background: '#f1f5f9', borderRadius: 8, padding: 14, fontSize: 13, color: '#334155', textAlign: 'left', marginBottom: 24, lineHeight: 1.5 }}>
            <div style={{ fontWeight: 600, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              <UserCheck size={16} color="#4f46e5" /> Secure Applicant Identity
            </div>
            Sign in to access your centralized profile, form auto-detection, and AI-tailored answers.
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <button
              onClick={handleGoogleLogin}
              disabled={authLoading}
              className="btn btn-primary"
              style={{ width: '100%', padding: '11px 16px', fontSize: 14, fontWeight: 600 }}
            >
              <Globe size={18} /> {authLoading ? 'Signing in...' : 'Sign In with Google'}
            </button>

            <button
              onClick={handleDevLogin}
              disabled={authLoading}
              className="btn btn-secondary"
              style={{ width: '100%', padding: '10px 16px', fontSize: 13 }}
            >
              Quick Demo Sign In (saikondareddypala@gmail.com)
            </button>
          </div>

          <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 24 }}>
            Complies with Chrome Manifest V3 security standards. No domain or university restrictions.
          </p>
        </div>
      </div>
    );
  }

  // If user needs to complete onboarding wizard
  if (showWizard) {
    return (
      <div className="dashboard-root">
        <header className="dashboard-header">
          <div className="dashboard-header-brand">
            <div className="dashboard-logo-badge">
              <Sparkles size={20} />
            </div>
            <div className="dashboard-title-wrap">
              <span className="dashboard-title">ApplyForMe Setup</span>
              <span className="dashboard-tagline">Applicant Profile Wizard</span>
            </div>
          </div>
          <button onClick={handleLogout} className="btn btn-secondary btn-sm">
            <LogOut size={13} /> Logout
          </button>
        </header>

        <OnboardingWizard
          user={user}
          onCompleted={(savedProfile) => {
            setProfile(savedProfile);
            setShowWizard(false);
            showToast('Profile setup complete! Welcome to your dashboard.');
            refreshUserData();
          }}
          onCancel={profile?.onboardingCompleted ? () => setShowWizard(false) : undefined}
        />
      </div>
    );
  }

  const completionScore = completion?.completionPercentage ?? profile?.completionPercentage ?? 0;
  const missingFields = completion?.missingRequired ?? [];
  const suggestions = completion?.suggestions ?? [];

  return (
    <div className="dashboard-root">
      {/* Toast Notification */}
      {feedback && (
        <div
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 100,
            background: feedback.type === 'success' ? '#10b981' : '#ef4444',
            color: '#fff',
            padding: '12px 20px',
            borderRadius: 8,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            fontSize: 13,
            fontWeight: 500
          }}
        >
          {feedback.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Header */}
      <header className="dashboard-header">
        <div className="dashboard-header-brand">
          <div className="dashboard-logo-badge">
            <Sparkles size={20} />
          </div>
          <div className="dashboard-title-wrap">
            <div className="dashboard-title-row">
              <span className="dashboard-title">ApplyForMe</span>
              <span className="badge badge-primary">SaaS Hub</span>
            </div>
            <span className="dashboard-tagline">One Profile. Smarter Applications.</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {user.picture && !avatarError ? (
              <img
                src={user.picture}
                alt={user.name}
                onError={() => setAvatarError(true)}
                style={{ width: 34, height: 34, borderRadius: '50%', objectFit: 'cover', border: '1px solid #e2e8f0' }}
              />
            ) : (
              <div style={{ width: 34, height: 34, borderRadius: '50%', background: '#eef2ff', color: '#4f46e5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: 14 }}>
                {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
              </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#0f172a' }}>{user.name}</span>
              <span style={{ fontSize: 11, color: '#64748b' }}>{user.email}</span>
            </div>
          </div>

          <button onClick={handleLogout} className="btn btn-secondary btn-sm" title="Sign out">
            <LogOut size={13} /> Logout
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="dashboard-main">
        {/* Metric Statistics Row */}
        <div className="stats-grid">
          <div className="stat-card" onClick={() => setActiveTab('overview')} style={{ cursor: 'pointer' }}>
            <div className="stat-info">
              <span className="stat-label">Profile Strength</span>
              <span className="stat-value">{completionScore}%</span>
            </div>
            <div className="stat-icon-wrap stat-icon-primary">
              <TrendingUp size={22} />
            </div>
          </div>

          <div className="stat-card" onClick={() => setActiveTab('resumes')} style={{ cursor: 'pointer' }}>
            <div className="stat-info">
              <span className="stat-label">Uploaded Resumes</span>
              <span className="stat-value">{resumes.length}</span>
            </div>
            <div className="stat-icon-wrap stat-icon-secondary">
              <FileText size={22} />
            </div>
          </div>

          <div className="stat-card" onClick={() => setActiveTab('applications')} style={{ cursor: 'pointer' }}>
            <div className="stat-info">
              <span className="stat-label">Applications</span>
              <span className="stat-value">{applications.length}</span>
            </div>
            <div className="stat-icon-wrap stat-icon-success">
              <Briefcase size={22} />
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-info">
              <span className="stat-label">AI Runtime</span>
              <span className="stat-value" style={{ fontSize: 15, color: '#047857' }}>Ollama Local</span>
            </div>
            <div className="stat-icon-wrap stat-icon-warning">
              <Cpu size={22} />
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="dashboard-tabs" style={{ overflowX: 'auto', whiteSpace: 'nowrap' }}>
          <button
            onClick={() => setActiveTab('overview')}
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          >
            <TrendingUp size={15} /> Overview
          </button>
          <button
            onClick={() => setActiveTab('personal')}
            className={`tab-btn ${activeTab === 'personal' ? 'active' : ''}`}
          >
            <UserCheck size={15} /> Personal Info
          </button>
          <button
            onClick={() => setActiveTab('education')}
            className={`tab-btn ${activeTab === 'education' ? 'active' : ''}`}
          >
            <GraduationCap size={15} /> Education
          </button>
          <button
            onClick={() => setActiveTab('skills')}
            className={`tab-btn ${activeTab === 'skills' ? 'active' : ''}`}
          >
            <Code size={15} /> Skills
          </button>
          <button
            onClick={() => setActiveTab('experience')}
            className={`tab-btn ${activeTab === 'experience' ? 'active' : ''}`}
          >
            <Briefcase size={15} /> Experience & Projects
          </button>
          <button
            onClick={() => setActiveTab('resumes')}
            className={`tab-btn ${activeTab === 'resumes' ? 'active' : ''}`}
          >
            <FileText size={15} /> Resumes ({resumes.length})
          </button>
          <button
            onClick={() => setActiveTab('career')}
            className={`tab-btn ${activeTab === 'career' ? 'active' : ''}`}
          >
            <Compass size={15} /> Career Preferences
          </button>
          <button
            onClick={() => setActiveTab('applications')}
            className={`tab-btn ${activeTab === 'applications' ? 'active' : ''}`}
          >
            <Briefcase size={15} /> Applications ({applications.length})
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
          >
            <Settings size={15} /> Settings
          </button>
        </div>

        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div className="content-grid">
            {/* Left Sidebar: Score & Suggestions */}
            <div>
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    <TrendingUp size={16} color="#4f46e5" /> Profile Completion
                  </h3>
                  <span className="badge badge-primary">{completionScore}%</span>
                </div>

                <div className="progress-bar-track">
                  <div className="progress-bar-fill" style={{ width: `${completionScore}%` }} />
                </div>

                <p style={{ fontSize: 12, color: '#64748b', marginTop: 10, marginBottom: 14 }}>
                  {completionScore >= 80
                    ? 'Excellent! Your profile is ready for automatic form filling and AI generation.'
                    : 'Add missing details to maximize auto-fill accuracy across internship portals.'}
                </p>

                {missingFields.length > 0 && (
                  <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 8, padding: 12, marginTop: 10 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#b45309', marginBottom: 6 }}>
                      Missing Required Fields:
                    </div>
                    <ul style={{ paddingLeft: 18, fontSize: 12, color: '#92400e' }}>
                      {missingFields.map((f, i) => (
                        <li key={i} style={{ marginBottom: 3 }}>{f}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div style={{ marginTop: 16 }}>
                  <button
                    onClick={() => setShowWizard(true)}
                    className="btn btn-secondary btn-sm"
                    style={{ width: '100%' }}
                  >
                    <Sparkles size={14} /> Re-run Setup Wizard
                  </button>
                </div>
              </div>

              {/* Suggestions */}
              {suggestions.length > 0 && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">
                      <Star size={16} color="#f59e0b" /> Recommendations
                    </h3>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {suggestions.map((sug, i) => (
                      <div key={i} style={{ fontSize: 12, color: '#475569', display: 'flex', alignItems: 'flex-start', gap: 6 }}>
                        <span style={{ color: '#4f46e5', fontWeight: 700 }}>•</span>
                        <span>{sug}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Main Overview Column */}
            <div>
              {/* Profile Summary Card */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    <UserCheck size={16} color="#4f46e5" /> Applicant Summary
                  </h3>
                  <button onClick={() => setActiveTab('personal')} className="btn btn-secondary btn-sm">
                    Edit Info
                  </button>
                </div>

                <div className="info-grid">
                  <div className="info-item">
                    <span className="info-label">Full Name</span>
                    <span className="info-value">{profile?.personalInformation?.fullName || user.name}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Email</span>
                    <span className="info-value">{profile?.personalInformation?.email || user.email}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Phone</span>
                    <span className="info-value">{profile?.personalInformation?.phone || <span className="info-empty">Not set</span>}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Location</span>
                    <span className="info-value">
                      {[profile?.personalInformation?.city, profile?.personalInformation?.country].filter(Boolean).join(', ') || <span className="info-empty">Not set</span>}
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Education</span>
                    <span className="info-value">
                      {profile?.education && profile.education.length > 0
                        ? `${profile.education[0].degree} (${profile.education[0].institution || profile.education[0].college})`
                        : <span className="info-empty">Not set</span>}
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Default Resume</span>
                    <span className="info-value">
                      {resumes.find(r => r.isDefault)?.title || (resumes[0]?.title ?? <span className="info-empty">No resume uploaded</span>)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Skills Snapshot */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    <Code size={16} color="#4f46e5" /> Skills Snapshot
                  </h3>
                  <button onClick={() => setActiveTab('skills')} className="btn btn-secondary btn-sm">
                    Manage Skills
                  </button>
                </div>

                <div className="tags-cloud">
                  {(profile?.skills?.programmingLanguages || []).map(s => (
                    <span key={s} className="tag-badge tag-badge-primary">{s}</span>
                  ))}
                  {(profile?.skills?.frameworks || []).map(s => (
                    <span key={s} className="tag-badge">{s}</span>
                  ))}
                  {(profile?.skills?.databases || []).map(s => (
                    <span key={s} className="tag-badge">{s}</span>
                  ))}
                  {(profile?.skills?.cloud || []).map(s => (
                    <span key={s} className="tag-badge">{s}</span>
                  ))}
                  {(!profile?.skills || Object.values(profile.skills).every(arr => !arr || arr.length === 0)) && (
                    <span className="info-empty" style={{ fontSize: 13 }}>No skills added yet.</span>
                  )}
                </div>
              </div>

              {/* Career Goal Card */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    <Compass size={16} color="#4f46e5" /> Career Intent
                  </h3>
                  <button onClick={() => setActiveTab('career')} className="btn btn-secondary btn-sm">
                    Edit Goals
                  </button>
                </div>

                <div style={{ fontSize: 13, color: '#334155', lineHeight: 1.6 }}>
                  <strong>Objective: </strong>
                  {profile?.careerPreferences?.careerObjective || <span className="info-empty">No career objective specified yet.</span>}
                </div>

                <div style={{ marginTop: 10, fontSize: 13, color: '#334155', lineHeight: 1.6 }}>
                  <strong>Summary: </strong>
                  {profile?.careerPreferences?.professionalSummary || <span className="info-empty">No professional summary specified yet.</span>}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Personal Information */}
        {activeTab === 'personal' && profile && (
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <UserCheck size={18} color="#4f46e5" /> Personal Information
              </h3>
              <button onClick={handleSaveProfile} disabled={saving} className="btn btn-primary btn-sm">
                <Save size={14} /> {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
              <div>
                <label className="info-label">First Name</label>
                <input
                  type="text"
                  value={profile.personalInformation?.firstName || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, firstName: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>

              <div>
                <label className="info-label">Last Name</label>
                <input
                  type="text"
                  value={profile.personalInformation?.lastName || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, lastName: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>

              <div>
                <label className="info-label">Full Name</label>
                <input
                  type="text"
                  value={profile.personalInformation?.fullName || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, fullName: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>

              <div>
                <label className="info-label">Email Address</label>
                <input
                  type="email"
                  value={profile.personalInformation?.email || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, email: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>

              <div>
                <label className="info-label">Phone</label>
                <input
                  type="tel"
                  value={profile.personalInformation?.phone || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, phone: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>

              <div>
                <label className="info-label">Date of Birth</label>
                <input
                  type="date"
                  value={profile.personalInformation?.dateOfBirth || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, dateOfBirth: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '7px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>

              <div>
                <label className="info-label">City</label>
                <input
                  type="text"
                  value={profile.personalInformation?.city || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, city: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>

              <div>
                <label className="info-label">State / Province</label>
                <input
                  type="text"
                  value={profile.personalInformation?.state || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, state: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>

              <div>
                <label className="info-label">Country</label>
                <input
                  type="text"
                  value={profile.personalInformation?.country || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, country: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>
            </div>

            <div style={{ marginTop: 16 }}>
              <label className="info-label">Address</label>
              <input
                type="text"
                value={profile.personalInformation?.address || ''}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    personalInformation: { ...profile.personalInformation, address: e.target.value }
                  })
                }
                style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16, marginTop: 16 }}>
              <div>
                <label className="info-label">LinkedIn URL</label>
                <input
                  type="url"
                  value={profile.personalInformation?.linkedin || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, linkedin: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>

              <div>
                <label className="info-label">GitHub URL</label>
                <input
                  type="url"
                  value={profile.personalInformation?.github || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, github: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>

              <div>
                <label className="info-label">Portfolio URL</label>
                <input
                  type="url"
                  value={profile.personalInformation?.portfolio || ''}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      personalInformation: { ...profile.personalInformation, portfolio: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Education */}
        {activeTab === 'education' && profile && (
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <GraduationCap size={18} color="#4f46e5" /> Educational Background
              </h3>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() =>
                    setProfile({
                      ...profile,
                      education: [
                        ...(profile.education || []),
                        { institution: '', degree: 'B.Tech', specialization: '', graduationYear: '2026', cgpa: '' }
                      ]
                    })
                  }
                >
                  <Plus size={14} /> Add Degree
                </button>
                <button onClick={handleSaveProfile} disabled={saving} className="btn btn-primary btn-sm">
                  <Save size={14} /> Save
                </button>
              </div>
            </div>

            {(profile.education || []).map((edu, idx) => (
              <div key={idx} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 16, marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>Degree #{idx + 1}</span>
                  <button
                    type="button"
                    onClick={() =>
                      setProfile({
                        ...profile,
                        education: profile.education.filter((_, i) => i !== idx)
                      })
                    }
                    style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}
                  >
                    <Trash2 size={13} /> Remove
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
                  <div>
                    <label className="info-label">Institution / College</label>
                    <input
                      type="text"
                      value={edu.institution || edu.college || ''}
                      onChange={(e) => {
                        const copy = [...profile.education];
                        copy[idx].institution = e.target.value;
                        copy[idx].college = e.target.value;
                        setProfile({ ...profile, education: copy });
                      }}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                    />
                  </div>

                  <div>
                    <label className="info-label">Degree</label>
                    <input
                      type="text"
                      value={edu.degree || ''}
                      onChange={(e) => {
                        const copy = [...profile.education];
                        copy[idx].degree = e.target.value;
                        setProfile({ ...profile, education: copy });
                      }}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                    />
                  </div>

                  <div>
                    <label className="info-label">Specialization / Branch</label>
                    <input
                      type="text"
                      value={edu.specialization || edu.branch || ''}
                      onChange={(e) => {
                        const copy = [...profile.education];
                        copy[idx].specialization = e.target.value;
                        copy[idx].branch = e.target.value;
                        setProfile({ ...profile, education: copy });
                      }}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                    />
                  </div>

                  <div>
                    <label className="info-label">Graduation Year</label>
                    <input
                      type="text"
                      value={edu.graduationYear || ''}
                      onChange={(e) => {
                        const copy = [...profile.education];
                        copy[idx].graduationYear = e.target.value;
                        setProfile({ ...profile, education: copy });
                      }}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                    />
                  </div>

                  <div>
                    <label className="info-label">CGPA / Percentage</label>
                    <input
                      type="text"
                      value={edu.cgpa || ''}
                      onChange={(e) => {
                        const copy = [...profile.education];
                        copy[idx].cgpa = e.target.value;
                        setProfile({ ...profile, education: copy });
                      }}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                    />
                  </div>

                  <div>
                    <label className="info-label">Active Backlogs</label>
                    <input
                      type="text"
                      value={edu.backlogs || '0'}
                      onChange={(e) => {
                        const copy = [...profile.education];
                        copy[idx].backlogs = e.target.value;
                        setProfile({ ...profile, education: copy });
                      }}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Tab 4: Skills */}
        {activeTab === 'skills' && profile && (
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <Code size={18} color="#4f46e5" /> Categorized Skills
              </h3>
              <button onClick={handleSaveProfile} disabled={saving} className="btn btn-primary btn-sm">
                <Save size={14} /> Save Skills
              </button>
            </div>

            {(
              [
                { key: 'programmingLanguages', label: 'Programming Languages' },
                { key: 'frameworks', label: 'Frameworks & Libraries' },
                { key: 'databases', label: 'Databases & Storage' },
                { key: 'cloud', label: 'Cloud Platforms' },
                { key: 'devops', label: 'DevOps & Tooling' },
                { key: 'aiMl', label: 'AI & Machine Learning' },
                { key: 'tools', label: 'Developer Tools' },
                { key: 'softSkills', label: 'Soft Skills' }
              ] as const
            ).map((cat) => {
              const list = (profile.skills[cat.key] as string[]) || [];
              return (
                <div key={cat.key} style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#1e293b', marginBottom: 6 }}>
                    {cat.label} ({list.length})
                  </label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                    {list.map((tag) => (
                      <span
                        key={tag}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          padding: '4px 10px',
                          borderRadius: 6,
                          background: '#eef2ff',
                          color: '#4338ca',
                          fontSize: 12,
                          fontWeight: 500,
                          border: '1px solid #c7d2fe'
                        }}
                      >
                        {tag}
                        <button
                          type="button"
                          onClick={() => handleRemoveSkillTag(cat.key, tag)}
                          style={{ background: 'none', border: 'none', color: '#6366f1', cursor: 'pointer', padding: 0 }}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    <input
                      type="text"
                      placeholder={`Add to ${cat.label}`}
                      value={newSkillTag[cat.key] || ''}
                      onChange={(e) => setNewSkillTag({ ...newSkillTag, [cat.key]: e.target.value })}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleAddSkillTag(cat.key);
                        }
                      }}
                      style={{ flex: 1, padding: '7px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                    />
                    <button
                      type="button"
                      onClick={() => handleAddSkillTag(cat.key)}
                      className="btn btn-secondary btn-sm"
                    >
                      Add
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Tab 5: Experience & Projects */}
        {activeTab === 'experience' && profile && (
          <div>
            {/* Experience */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <Briefcase size={18} color="#4f46e5" /> Work Experiences & Internships
                </h3>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() =>
                      setProfile({
                        ...profile,
                        experiences: [
                          ...(profile.experiences || []),
                          { company: '', role: '', employmentType: 'Full-time', startDate: '', endDate: '', currentlyWorking: false, technologies: [], description: '' }
                        ]
                      })
                    }
                  >
                    <Plus size={14} /> Add Role
                  </button>
                  <button onClick={handleSaveProfile} disabled={saving} className="btn btn-primary btn-sm">
                    <Save size={14} /> Save
                  </button>
                </div>
              </div>

              {(profile.experiences || []).map((exp, idx) => (
                <div key={idx} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 16, marginBottom: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>Experience #{idx + 1}</span>
                    <button
                      type="button"
                      onClick={() =>
                        setProfile({
                          ...profile,
                          experiences: profile.experiences.filter((_, i) => i !== idx)
                        })
                      }
                      style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}
                    >
                      <Trash2 size={13} /> Remove
                    </button>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 10 }}>
                    <div>
                      <label className="info-label">Company</label>
                      <input
                        type="text"
                        value={exp.company}
                        onChange={(e) => {
                          const copy = [...profile.experiences];
                          copy[idx].company = e.target.value;
                          setProfile({ ...profile, experiences: copy });
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      />
                    </div>
                    <div>
                      <label className="info-label">Role</label>
                      <input
                        type="text"
                        value={exp.role || exp.title || ''}
                        onChange={(e) => {
                          const copy = [...profile.experiences];
                          copy[idx].role = e.target.value;
                          copy[idx].title = e.target.value;
                          setProfile({ ...profile, experiences: copy });
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      />
                    </div>
                    <div>
                      <label className="info-label">Start Date</label>
                      <input
                        type="text"
                        value={exp.startDate}
                        onChange={(e) => {
                          const copy = [...profile.experiences];
                          copy[idx].startDate = e.target.value;
                          setProfile({ ...profile, experiences: copy });
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      />
                    </div>
                    <div>
                      <label className="info-label">End Date</label>
                      <input
                        type="text"
                        value={exp.endDate || ''}
                        onChange={(e) => {
                          const copy = [...profile.experiences];
                          copy[idx].endDate = e.target.value;
                          setProfile({ ...profile, experiences: copy });
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="info-label">Description & Achievements</label>
                    <textarea
                      rows={2}
                      value={exp.description}
                      onChange={(e) => {
                        const copy = [...profile.experiences];
                        copy[idx].description = e.target.value;
                        setProfile({ ...profile, experiences: copy });
                      }}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13, resize: 'vertical' }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Projects */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <FolderGit2 size={18} color="#4f46e5" /> Featured Projects
                </h3>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() =>
                      setProfile({
                        ...profile,
                        projects: [
                          ...(profile.projects || []),
                          { projectName: '', description: '', technologies: [], githubUrl: '', liveUrl: '' }
                        ]
                      })
                    }
                  >
                    <Plus size={14} /> Add Project
                  </button>
                  <button onClick={handleSaveProfile} disabled={saving} className="btn btn-primary btn-sm">
                    <Save size={14} /> Save
                  </button>
                </div>
              </div>

              {(profile.projects || []).map((proj, idx) => (
                <div key={idx} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 16, marginBottom: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>Project #{idx + 1}</span>
                    <button
                      type="button"
                      onClick={() =>
                        setProfile({
                          ...profile,
                          projects: profile.projects.filter((_, i) => i !== idx)
                        })
                      }
                      style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}
                    >
                      <Trash2 size={13} /> Remove
                    </button>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 10 }}>
                    <div>
                      <label className="info-label">Project Name</label>
                      <input
                        type="text"
                        value={proj.projectName}
                        onChange={(e) => {
                          const copy = [...profile.projects];
                          copy[idx].projectName = e.target.value;
                          setProfile({ ...profile, projects: copy });
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      />
                    </div>
                    <div>
                      <label className="info-label">GitHub URL</label>
                      <input
                        type="url"
                        value={proj.githubUrl || ''}
                        onChange={(e) => {
                          const copy = [...profile.projects];
                          copy[idx].githubUrl = e.target.value;
                          setProfile({ ...profile, projects: copy });
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      />
                    </div>
                    <div>
                      <label className="info-label">Live URL</label>
                      <input
                        type="url"
                        value={proj.liveUrl || ''}
                        onChange={(e) => {
                          const copy = [...profile.projects];
                          copy[idx].liveUrl = e.target.value;
                          setProfile({ ...profile, projects: copy });
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="info-label">Description</label>
                    <textarea
                      rows={2}
                      value={proj.description}
                      onChange={(e) => {
                        const copy = [...profile.projects];
                        copy[idx].description = e.target.value;
                        setProfile({ ...profile, projects: copy });
                      }}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13, resize: 'vertical' }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 6: Resumes */}
        {activeTab === 'resumes' && (
          <div>
            {/* Upload New Resume */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <UploadCloud size={18} color="#4f46e5" /> Upload PDF Resume
                </h3>
              </div>

              <form onSubmit={handleResumeUpload}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14, marginBottom: 16 }}>
                  <div>
                    <label className="info-label">Resume Title / Version</label>
                    <input
                      type="text"
                      value={uploadTitle}
                      onChange={(e) => setUploadTitle(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      placeholder="e.g. Full Stack 2026"
                      required
                    />
                  </div>

                  <div>
                    <label className="info-label">Category</label>
                    <select
                      value={uploadCategory}
                      onChange={(e) => setUploadCategory(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                    >
                      <option value="General">General</option>
                      <option value="Software Engineer">Software Engineer</option>
                      <option value="Frontend Developer">Frontend Developer</option>
                      <option value="Backend Developer">Backend Developer</option>
                      <option value="AI / ML Engineer">AI / ML Engineer</option>
                    </select>
                  </div>

                  <div>
                    <label className="info-label">Select PDF File (Max 5MB)</label>
                    <input
                      type="file"
                      accept=".pdf,application/pdf"
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          setUploadFile(e.target.files[0]);
                        }
                      }}
                      style={{ width: '100%', padding: '6px', fontSize: 12 }}
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isUploading}
                  className="btn btn-primary btn-sm"
                >
                  <UploadCloud size={14} /> {isUploading ? 'Uploading...' : 'Upload Resume'}
                </button>
              </form>
            </div>

            {/* List Resumes */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <FileText size={18} color="#4f46e5" /> Uploaded Resumes ({resumes.length})
                </h3>
              </div>

              {resumes.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">
                    <FileText size={24} />
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>
                    No resumes uploaded yet
                  </div>
                  <div style={{ fontSize: 12, color: '#64748b' }}>
                    Upload your first PDF resume above to enable one-click document selection during applications.
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {resumes.map((r) => (
                    <div
                      key={r._id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: 16,
                        border: r.isDefault ? '2px solid #4f46e5' : '1px solid #e2e8f0',
                        borderRadius: 8,
                        background: r.isDefault ? '#f5f3ff' : '#ffffff'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                        <div style={{ width: 40, height: 40, borderRadius: 8, background: '#fee2e2', color: '#dc2626', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <FileText size={20} />
                        </div>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontSize: 14, fontWeight: 600, color: '#0f172a' }}>{r.title}</span>
                            {r.isDefault && (
                              <span className="badge badge-primary" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                <Check size={12} /> Primary Default
                              </span>
                            )}
                            {r.category && <span className="badge badge-slate">{r.category}</span>}
                          </div>
                          <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                            {r.fileName} • {r.fileSize ? `${(r.fileSize / 1024).toFixed(1)} KB` : 'PDF'} • Uploaded{' '}
                            {new Date(r.uploadedAt).toLocaleDateString()}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {!r.isDefault && (
                          <button
                            onClick={() => handleSetDefaultResume(r._id)}
                            className="btn btn-secondary btn-sm"
                          >
                            Set Default
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteResume(r._id)}
                          className="btn btn-danger btn-sm"
                          title="Delete resume"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 7: Career Preferences */}
        {activeTab === 'career' && profile && (
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <Compass size={18} color="#4f46e5" /> Career Preferences & Search Intent
              </h3>
              <button onClick={handleSaveProfile} disabled={saving} className="btn btn-primary btn-sm">
                <Save size={14} /> Save Preferences
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16, marginBottom: 16 }}>
              <div>
                <label className="info-label">Availability</label>
                <input
                  type="text"
                  value={profile.careerPreferences?.availability || 'Immediate'}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      careerPreferences: { ...profile.careerPreferences, availability: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>

              <div>
                <label className="info-label">Work Mode Preference</label>
                <select
                  value={profile.careerPreferences?.workModes?.[0] || 'Remote'}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      careerPreferences: { ...profile.careerPreferences, workModes: [e.target.value] }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                >
                  <option value="Remote">Remote</option>
                  <option value="Hybrid">Hybrid</option>
                  <option value="On-site">On-site</option>
                  <option value="Flexible">Flexible</option>
                </select>
              </div>

              <div>
                <label className="info-label">Work Authorization</label>
                <input
                  type="text"
                  value={profile.careerPreferences?.workAuthorization || 'Authorized to work'}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      careerPreferences: { ...profile.careerPreferences, workAuthorization: e.target.value }
                    })
                  }
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label className="info-label">Career Objective</label>
              <textarea
                rows={2}
                value={profile.careerPreferences?.careerObjective || profile.careerPreferences?.careerObjectives || ''}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    careerPreferences: {
                      ...profile.careerPreferences,
                      careerObjective: e.target.value,
                      careerObjectives: e.target.value
                    }
                  })
                }
                style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13, resize: 'vertical' }}
              />
            </div>

            <div>
              <label className="info-label">Professional Summary</label>
              <textarea
                rows={4}
                value={profile.careerPreferences?.professionalSummary || ''}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    careerPreferences: { ...profile.careerPreferences, professionalSummary: e.target.value }
                  })
                }
                style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13, resize: 'vertical' }}
              />
            </div>
          </div>
        )}

        {/* Tab 8: Tracked Applications */}
        {activeTab === 'applications' && (
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <Briefcase size={18} color="#4f46e5" /> Tracked Applications ({applications.length})
              </h3>
            </div>

            {applications.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <Briefcase size={24} />
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>
                  No applications recorded yet
                </div>
                <div style={{ fontSize: 12, color: '#64748b' }}>
                  When you autofill or submit applications on company portals, they will appear here.
                </div>
              </div>
            ) : (
              <div className="table-wrap">
                <table className="app-table">
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Job Title</th>
                      <th>Status</th>
                      <th>Date</th>
                      <th>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {applications.map((app) => (
                      <tr key={app._id}>
                        <td style={{ fontWeight: 600 }}>{app.companyName}</td>
                        <td>
                          {app.jobUrl ? (
                            <a href={app.jobUrl} target="_blank" rel="noreferrer" style={{ color: '#4f46e5', textDecoration: 'none' }}>
                              {app.jobTitle} <ExternalLink size={12} style={{ display: 'inline' }} />
                            </a>
                          ) : (
                            app.jobTitle
                          )}
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              app.status === 'Applied'
                                ? 'badge-primary'
                                : app.status === 'Interview'
                                ? 'badge-warning'
                                : app.status === 'Selected'
                                ? 'badge-success'
                                : 'badge-slate'
                            }`}
                          >
                            {app.status}
                          </span>
                        </td>
                        <td>{new Date(app.appliedAt).toLocaleDateString()}</td>
                        <td style={{ color: '#64748b' }}>{app.notes || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 9: Settings */}
        {activeTab === 'settings' && (
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <Settings size={18} color="#4f46e5" /> Account & System Configuration
              </h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div>
                <h4 style={{ fontSize: 14, fontWeight: 600, color: '#1e293b', marginBottom: 6 }}>Connected Identity</h4>
                <div style={{ fontSize: 13, color: '#475569' }}>
                  Signed in as <strong>{user.name}</strong> ({user.email})
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: 14, fontWeight: 600, color: '#1e293b', marginBottom: 6 }}>Profile Onboarding</h4>
                <p style={{ fontSize: 13, color: '#64748b', marginBottom: 10 }}>
                  You can re-launch the 7-step guided setup wizard anytime to systematically review and update your information.
                </p>
                <button onClick={() => setShowWizard(true)} className="btn btn-secondary btn-sm">
                  <Sparkles size={14} /> Launch Setup Wizard
                </button>
              </div>

              <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 16 }}>
                <h4 style={{ fontSize: 14, fontWeight: 600, color: '#dc2626', marginBottom: 6 }}>Danger Zone</h4>
                <p style={{ fontSize: 13, color: '#64748b', marginBottom: 10 }}>
                  Log out of your session on this Chrome extension.
                </p>
                <button onClick={handleLogout} className="btn btn-danger btn-sm">
                  <LogOut size={14} /> Log Out
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

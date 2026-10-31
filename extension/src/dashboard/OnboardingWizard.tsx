import React, { useState } from 'react';
import { api } from '../lib/api';
import { User, ApplicantProfile, EducationItem, ExperienceItem, ProjectItem } from '../lib/types';
import {
  User as UserIcon,
  GraduationCap,
  Code,
  Briefcase,
  FileText,
  Compass,
  CheckCircle,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  Plus,
  Trash2,
  UploadCloud,
  Check,
  AlertCircle
} from 'lucide-react';

interface OnboardingWizardProps {
  user: User;
  onCompleted: (profile: ApplicantProfile) => void;
  onCancel?: () => void;
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ user, onCompleted, onCancel }) => {
  const [step, setStep] = useState<number>(1);
  const [saving, setSaving] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  // Form State initialized with user info
  const nameParts = (user.name || '').trim().split(' ');
  const [personal, setPersonal] = useState({
    firstName: nameParts[0] || '',
    lastName: nameParts.slice(1).join(' ') || '',
    fullName: user.name || '',
    email: user.email || '',
    phone: '',
    city: '',
    state: '',
    country: '',
    address: '',
    dateOfBirth: '',
    gender: '',
    linkedin: '',
    github: '',
    portfolio: ''
  });

  // Education state
  const [educationList, setEducationList] = useState<EducationItem[]>([
    {
      institution: '',
      degree: 'B.Tech',
      specialization: 'Computer Science',
      graduationYear: new Date().getFullYear().toString(),
      cgpa: '',
      gradingSystem: '10-point scale',
      tenthPercentage: '',
      twelfthPercentage: '',
      backlogs: '0'
    }
  ]);

  // Skills state
  const [skills, setSkills] = useState<{
    programmingLanguages: string[];
    frameworks: string[];
    databases: string[];
    cloud: string[];
    devops: string[];
    aiMl: string[];
    tools: string[];
    softSkills: string[];
  }>({
    programmingLanguages: ['Python', 'TypeScript', 'JavaScript'],
    frameworks: ['React', 'FastAPI', 'Node.js'],
    databases: ['MongoDB', 'PostgreSQL'],
    cloud: ['AWS'],
    devops: ['Docker', 'Git'],
    aiMl: ['LangChain'],
    tools: ['VS Code', 'Postman'],
    softSkills: ['Problem Solving', 'Teamwork', 'Communication']
  });

  const [inputTag, setInputTag] = useState<{ [category: string]: string }>({});

  // Experiences
  const [experiences, setExperiences] = useState<ExperienceItem[]>([
    {
      company: '',
      role: '',
      employmentType: 'Full-time',
      startDate: '',
      endDate: '',
      currentlyWorking: false,
      technologies: [],
      description: ''
    }
  ]);

  // Projects
  const [projects, setProjects] = useState<ProjectItem[]>([
    {
      projectName: '',
      description: '',
      technologies: [],
      githubUrl: '',
      liveUrl: ''
    }
  ]);

  // Resume Upload State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [resumeTitle, setResumeTitle] = useState<string>('Primary Resume');
  const [resumeCategory, setResumeCategory] = useState<string>('General');
  const [uploadSuccess, setUploadSuccess] = useState<boolean>(false);

  // Career Preferences
  const [career, setCareer] = useState({
    preferredRoles: ['Software Engineer', 'Full Stack Developer'],
    preferredIndustries: ['Technology', 'Software'],
    preferredLocations: ['Remote', 'Bangalore', 'San Francisco'],
    employmentTypes: ['Full-time', 'Internship'],
    workModes: ['Remote', 'Hybrid'],
    willingToRelocate: true,
    availability: 'Immediate',
    careerObjective: 'Aspiring software engineer eager to build reliable and scalable web applications.',
    professionalSummary: 'Dedicated developer with hands-on experience in full-stack web development and AI integrations.',
    expectedSalary: '',
    workAuthorization: 'Authorized to work'
  });

  // Tag helper
  const addTag = (category: keyof typeof skills) => {
    const val = (inputTag[category] || '').trim();
    if (!val) return;
    if (!skills[category].includes(val)) {
      setSkills(prev => ({ ...prev, [category]: [...prev[category], val] }));
    }
    setInputTag(prev => ({ ...prev, [category]: '' }));
  };

  const removeTag = (category: keyof typeof skills, tagToRemove: string) => {
    setSkills(prev => ({
      ...prev,
      [category]: prev[category].filter(t => t !== tagToRemove)
    }));
  };

  // Add tag for career roles/locations
  const addCareerTag = (field: 'preferredRoles' | 'preferredLocations', val: string) => {
    const trimmed = val.trim();
    if (!trimmed || career[field].includes(trimmed)) return;
    setCareer(prev => ({ ...prev, [field]: [...prev[field], trimmed] }));
  };

  const removeCareerTag = (field: 'preferredRoles' | 'preferredLocations', val: string) => {
    setCareer(prev => ({ ...prev, [field]: prev[field].filter(item => item !== val) }));
  };

  // Navigation handlers
  const handleNext = () => {
    setErrorMsg('');
    if (step === 1) {
      if (!personal.firstName.trim() || !personal.email.trim()) {
        setErrorMsg('Please enter your first name and email.');
        return;
      }
    }
    if (step < 7) {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    setErrorMsg('');
    if (step > 1) {
      setStep(step - 1);
    }
  };

  // Submit complete profile
  const handleFinalSubmit = async () => {
    setSaving(true);
    setErrorMsg('');
    try {
      // 1. Upload resume file if selected
      if (selectedFile) {
        try {
          await api.uploadResume(selectedFile, resumeTitle, resumeCategory, true);
        } catch (resErr: any) {
          console.warn('Resume upload warning during wizard:', resErr);
        }
      }

      // 2. Prepare profile document
      const fullName = personal.fullName.trim() || `${personal.firstName} ${personal.lastName}`.trim();
      const profilePayload: Partial<ApplicantProfile> = {
        personalInformation: {
          ...personal,
          fullName
        },
        education: educationList.filter(e => e.institution.trim() || e.degree.trim()),
        skills: {
          ...skills,
          cloudPlatforms: skills.cloud,
          tools: skills.tools,
          technicalSkills: [...skills.programmingLanguages, ...skills.frameworks]
        },
        experiences: experiences.filter(e => e.company.trim() || e.role.trim()),
        projects: projects.filter(p => p.projectName.trim()),
        professionalLinks: {
          linkedin: personal.linkedin,
          github: personal.github,
          portfolio: personal.portfolio
        },
        careerPreferences: {
          ...career,
          careerObjectives: career.careerObjective
        },
        onboardingCompleted: true
      };

      const saved = await api.createProfile(profilePayload);
      onCompleted(saved);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save profile. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Step names
  const stepTitles = [
    { num: 1, label: 'Personal Info', icon: UserIcon },
    { num: 2, label: 'Education', icon: GraduationCap },
    { num: 3, label: 'Skills', icon: Code },
    { num: 4, label: 'Experience & Projects', icon: Briefcase },
    { num: 5, label: 'Resume', icon: FileText },
    { num: 6, label: 'Career Preferences', icon: Compass },
    { num: 7, label: 'Review & Finish', icon: Sparkles }
  ];

  return (
    <div style={{ maxWidth: 860, margin: '20px auto', padding: '0 16px' }}>
      {/* Wizard Header */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '24px 28px', marginBottom: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
              <Sparkles size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a' }}>Welcome to ApplyForMe, {user.name || 'Applicant'}!</h2>
              <p style={{ fontSize: 13, color: '#64748b' }}>Complete your centralized profile once to enable smart autofill and AI applications.</p>
            </div>
          </div>
          <span className="badge badge-primary">Step {step} of 7</span>
        </div>

        {/* Stepper Progress Bar */}
        <div className="progress-bar-track" style={{ height: 6, margin: '14px 0' }}>
          <div className="progress-bar-fill" style={{ width: `${(step / 7) * 100}%` }} />
        </div>

        {/* Step Icons Row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, overflowX: 'auto', paddingTop: 6 }}>
          {stepTitles.map((s) => {
            const Icon = s.icon;
            const isDone = step > s.num;
            const isCurrent = step === s.num;
            return (
              <div
                key={s.num}
                onClick={() => setStep(s.num)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: 12,
                  fontWeight: isCurrent ? 600 : 500,
                  color: isCurrent ? '#4f46e5' : isDone ? '#10b981' : '#94a3b8',
                  cursor: 'pointer',
                  padding: '4px 6px'
                }}
              >
                <div
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: '50%',
                    background: isCurrent ? '#4f46e5' : isDone ? '#ecfdf5' : '#f1f5f9',
                    color: isCurrent ? '#fff' : isDone ? '#10b981' : '#94a3b8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 11,
                    fontWeight: 700
                  }}
                >
                  {isDone ? <Check size={14} /> : s.num}
                </div>
                <span>{s.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Error alert */}
      {errorMsg && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '12px 16px', color: '#b91c1c', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
          <AlertCircle size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Step Container Card */}
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 12, padding: 28, boxShadow: '0 2px 4px rgba(0,0,0,0.04)', marginBottom: 20 }}>
        {/* Step 1: Personal Information */}
        {step === 1 && (
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#0f172a', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
              <UserIcon size={18} color="#4f46e5" /> Personal Information
            </h3>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 20 }}>These details are used to fill out basic applicant info on career forms.</p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>First Name *</label>
                <input
                  type="text"
                  value={personal.firstName}
                  onChange={(e) => setPersonal({ ...personal, firstName: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="e.g. Alex"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Last Name</label>
                <input
                  type="text"
                  value={personal.lastName}
                  onChange={(e) => setPersonal({ ...personal, lastName: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="e.g. Rivera"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Email Address *</label>
                <input
                  type="email"
                  value={personal.email}
                  onChange={(e) => setPersonal({ ...personal, email: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="alex.rivera@example.com"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Phone Number</label>
                <input
                  type="tel"
                  value={personal.phone}
                  onChange={(e) => setPersonal({ ...personal, phone: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="+1 (555) 123-4567"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>City</label>
                <input
                  type="text"
                  value={personal.city}
                  onChange={(e) => setPersonal({ ...personal, city: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="e.g. Seattle"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>State / Province</label>
                <input
                  type="text"
                  value={personal.state}
                  onChange={(e) => setPersonal({ ...personal, state: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="e.g. WA"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Country</label>
                <input
                  type="text"
                  value={personal.country}
                  onChange={(e) => setPersonal({ ...personal, country: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="e.g. United States"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Date of Birth</label>
                <input
                  type="date"
                  value={personal.dateOfBirth}
                  onChange={(e) => setPersonal({ ...personal, dateOfBirth: e.target.value })}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>
            </div>

            <div style={{ marginTop: 16 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Street Address</label>
              <input
                type="text"
                value={personal.address}
                onChange={(e) => setPersonal({ ...personal, address: e.target.value })}
                style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                placeholder="123 Innovation Way, Apt 4B"
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginTop: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>LinkedIn URL</label>
                <input
                  type="url"
                  value={personal.linkedin}
                  onChange={(e) => setPersonal({ ...personal, linkedin: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="https://linkedin.com/in/username"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>GitHub URL</label>
                <input
                  type="url"
                  value={personal.github}
                  onChange={(e) => setPersonal({ ...personal, github: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="https://github.com/username"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Portfolio / Website</label>
                <input
                  type="url"
                  value={personal.portfolio}
                  onChange={(e) => setPersonal({ ...personal, portfolio: e.target.value })}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="https://yourportfolio.dev"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Education */}
        {step === 2 && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: '#0f172a', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <GraduationCap size={18} color="#4f46e5" /> Educational Background
                </h3>
                <p style={{ fontSize: 13, color: '#64748b' }}>Add your university degree, GPA, and graduation timeline.</p>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() =>
                  setEducationList([
                    ...educationList,
                    { institution: '', degree: 'M.S.', specialization: 'Computer Science', graduationYear: '2026', cgpa: '' }
                  ])
                }
              >
                <Plus size={14} /> Add Degree
              </button>
            </div>

            {educationList.map((edu, idx) => (
              <div key={idx} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 18, marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>Education #{idx + 1}</span>
                  {educationList.length > 1 && (
                    <button
                      type="button"
                      onClick={() => setEducationList(educationList.filter((_, i) => i !== idx))}
                      style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}
                    >
                      <Trash2 size={13} /> Remove
                    </button>
                  )}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>College / University *</label>
                    <input
                      type="text"
                      value={edu.institution}
                      onChange={(e) => {
                        const copy = [...educationList];
                        copy[idx].institution = e.target.value;
                        copy[idx].college = e.target.value;
                        setEducationList(copy);
                      }}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      placeholder="e.g. Stanford University"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Degree *</label>
                    <input
                      type="text"
                      value={edu.degree}
                      onChange={(e) => {
                        const copy = [...educationList];
                        copy[idx].degree = e.target.value;
                        setEducationList(copy);
                      }}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      placeholder="e.g. B.Tech / B.S."
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Specialization / Major</label>
                    <input
                      type="text"
                      value={edu.specialization}
                      onChange={(e) => {
                        const copy = [...educationList];
                        copy[idx].specialization = e.target.value;
                        copy[idx].branch = e.target.value;
                        setEducationList(copy);
                      }}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      placeholder="e.g. Computer Science"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Graduation Year</label>
                    <input
                      type="text"
                      value={edu.graduationYear}
                      onChange={(e) => {
                        const copy = [...educationList];
                        copy[idx].graduationYear = e.target.value;
                        setEducationList(copy);
                      }}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      placeholder="e.g. 2025"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>CGPA / Percentage</label>
                    <input
                      type="text"
                      value={edu.cgpa}
                      onChange={(e) => {
                        const copy = [...educationList];
                        copy[idx].cgpa = e.target.value;
                        setEducationList(copy);
                      }}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      placeholder="e.g. 3.8 / 10.0"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Active Backlogs</label>
                    <input
                      type="text"
                      value={edu.backlogs || '0'}
                      onChange={(e) => {
                        const copy = [...educationList];
                        copy[idx].backlogs = e.target.value;
                        setEducationList(copy);
                      }}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                      placeholder="0"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Step 3: Skills */}
        {step === 3 && (
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#0f172a', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <Code size={18} color="#4f46e5" /> Technical & Soft Skills
            </h3>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 20 }}>Categorized skills are matched against job requirements and inserted into application answers.</p>

            {(
              [
                { key: 'programmingLanguages', label: 'Programming Languages', placeholder: 'e.g. Python, Java, C++' },
                { key: 'frameworks', label: 'Frameworks & Libraries', placeholder: 'e.g. React, Next.js, FastAPI' },
                { key: 'databases', label: 'Databases & Storage', placeholder: 'e.g. PostgreSQL, Redis, MongoDB' },
                { key: 'cloud', label: 'Cloud Platforms', placeholder: 'e.g. AWS, GCP, Azure' },
                { key: 'devops', label: 'DevOps & CI/CD', placeholder: 'e.g. Docker, Kubernetes, GitHub Actions' },
                { key: 'aiMl', label: 'AI & Machine Learning', placeholder: 'e.g. Ollama, LangChain, PyTorch' },
                { key: 'tools', label: 'Developer Tools', placeholder: 'e.g. Git, VS Code, Linux' },
                { key: 'softSkills', label: 'Soft Skills', placeholder: 'e.g. Team Leadership, Problem Solving' }
              ] as const
            ).map((cat) => (
              <div key={cat.key} style={{ marginBottom: 18 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 6 }}>
                  {cat.label} ({skills[cat.key].length})
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                  {skills[cat.key].map((tag) => (
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
                        onClick={() => removeTag(cat.key, tag)}
                        style={{ background: 'none', border: 'none', color: '#6366f1', cursor: 'pointer', padding: 0, fontSize: 12 }}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type="text"
                    value={inputTag[cat.key] || ''}
                    onChange={(e) => setInputTag({ ...inputTag, [cat.key]: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addTag(cat.key);
                      }
                    }}
                    placeholder={cat.placeholder}
                    style={{ flex: 1, padding: '7px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  />
                  <button type="button" onClick={() => addTag(cat.key)} className="btn btn-secondary btn-sm">
                    Add
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Step 4: Experience & Projects */}
        {step === 4 && (
          <div>
            {/* Experience Section */}
            <div style={{ marginBottom: 28 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <div>
                  <h3 style={{ fontSize: 15, fontWeight: 600, color: '#0f172a', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Briefcase size={16} color="#4f46e5" /> Work Experience & Internships
                  </h3>
                  <p style={{ fontSize: 12, color: '#64748b' }}>Highlight your previous roles, accomplishments, and tech stack.</p>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() =>
                    setExperiences([
                      ...experiences,
                      { company: '', role: '', employmentType: 'Full-time', startDate: '', endDate: '', currentlyWorking: false, technologies: [], description: '' }
                    ])
                  }
                >
                  <Plus size={14} /> Add Experience
                </button>
              </div>

              {experiences.map((exp, idx) => (
                <div key={idx} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 16, marginBottom: 12 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 10 }}>
                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: '#475569', marginBottom: 3 }}>Company / Organization</label>
                      <input
                        type="text"
                        value={exp.company}
                        onChange={(e) => {
                          const c = [...experiences];
                          c[idx].company = e.target.value;
                          setExperiences(c);
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 12 }}
                        placeholder="e.g. Acme Corp"
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: '#475569', marginBottom: 3 }}>Role / Title</label>
                      <input
                        type="text"
                        value={exp.role}
                        onChange={(e) => {
                          const c = [...experiences];
                          c[idx].role = e.target.value;
                          c[idx].title = e.target.value;
                          setExperiences(c);
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 12 }}
                        placeholder="e.g. Frontend Engineer Intern"
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: '#475569', marginBottom: 3 }}>Start Date</label>
                      <input
                        type="text"
                        value={exp.startDate}
                        onChange={(e) => {
                          const c = [...experiences];
                          c[idx].startDate = e.target.value;
                          setExperiences(c);
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 12 }}
                        placeholder="e.g. May 2024"
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: '#475569', marginBottom: 3 }}>End Date</label>
                      <input
                        type="text"
                        value={exp.endDate || ''}
                        onChange={(e) => {
                          const c = [...experiences];
                          c[idx].endDate = e.target.value;
                          setExperiences(c);
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 12 }}
                        placeholder="e.g. Aug 2024 (or Present)"
                      />
                    </div>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: '#475569', marginBottom: 3 }}>Responsibilities & Impact</label>
                    <textarea
                      rows={2}
                      value={exp.description}
                      onChange={(e) => {
                        const c = [...experiences];
                        c[idx].description = e.target.value;
                        setExperiences(c);
                      }}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 12, resize: 'vertical' }}
                      placeholder="Engineered high-performance React modules, increasing page speed by 35%."
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Projects Section */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <div>
                  <h3 style={{ fontSize: 15, fontWeight: 600, color: '#0f172a', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Code size={16} color="#4f46e5" /> Featured Projects
                  </h3>
                  <p style={{ fontSize: 12, color: '#64748b' }}>Projects demonstrate practical implementation skills to recruiters.</p>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() =>
                    setProjects([
                      ...projects,
                      { projectName: '', description: '', technologies: [], githubUrl: '', liveUrl: '' }
                    ])
                  }
                >
                  <Plus size={14} /> Add Project
                </button>
              </div>

              {projects.map((proj, idx) => (
                <div key={idx} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 16, marginBottom: 12 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 10 }}>
                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: '#475569', marginBottom: 3 }}>Project Name</label>
                      <input
                        type="text"
                        value={proj.projectName}
                        onChange={(e) => {
                          const c = [...projects];
                          c[idx].projectName = e.target.value;
                          setProjects(c);
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 12 }}
                        placeholder="e.g. ApplyForMe Extension"
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: '#475569', marginBottom: 3 }}>GitHub URL</label>
                      <input
                        type="url"
                        value={proj.githubUrl || ''}
                        onChange={(e) => {
                          const c = [...projects];
                          c[idx].githubUrl = e.target.value;
                          setProjects(c);
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 12 }}
                        placeholder="https://github.com/..."
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: '#475569', marginBottom: 3 }}>Live Demo URL</label>
                      <input
                        type="url"
                        value={proj.liveUrl || ''}
                        onChange={(e) => {
                          const c = [...projects];
                          c[idx].liveUrl = e.target.value;
                          c[idx].projectUrl = e.target.value;
                          setProjects(c);
                        }}
                        style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 12 }}
                        placeholder="https://demo.app"
                      />
                    </div>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: '#475569', marginBottom: 3 }}>Description & Highlights</label>
                    <textarea
                      rows={2}
                      value={proj.description}
                      onChange={(e) => {
                        const c = [...projects];
                        c[idx].description = e.target.value;
                        setProjects(c);
                      }}
                      style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 12, resize: 'vertical' }}
                      placeholder="Built with React, FastAPI and Ollama LLM to streamline repetitive job applications."
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 5: Resume Upload */}
        {step === 5 && (
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#0f172a', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <FileText size={18} color="#4f46e5" /> Resume Document
            </h3>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 20 }}>Upload your latest PDF resume. (Maximum file size 5MB)</p>

            <div
              style={{
                border: '2px dashed #cbd5e1',
                borderRadius: 10,
                padding: '36px 20px',
                textAlign: 'center',
                background: selectedFile ? '#f0fdf4' : '#f8fafc',
                borderColor: selectedFile ? '#86efac' : '#cbd5e1',
                marginBottom: 20
              }}
            >
              <UploadCloud size={40} color={selectedFile ? '#16a34a' : '#64748b'} style={{ margin: '0 auto 12px' }} />
              {selectedFile ? (
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#15803d', marginBottom: 4 }}>
                    {selectedFile.name}
                  </div>
                  <div style={{ fontSize: 12, color: '#475569', marginBottom: 14 }}>
                    {(selectedFile.size / 1024).toFixed(1)} KB • PDF Document
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setSelectedFile(null)}
                  >
                    Choose Different File
                  </button>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>
                    Drop your PDF resume here or click to browse
                  </div>
                  <div style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>
                    Supports PDF format up to 5MB
                  </div>
                  <label className="btn btn-primary btn-sm" style={{ cursor: 'pointer' }}>
                    Select PDF
                    <input
                      type="file"
                      accept=".pdf,application/pdf"
                      style={{ display: 'none' }}
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          const file = e.target.files[0];
                          if (!file.name.toLowerCase().endsWith('.pdf')) {
                            setErrorMsg('Only PDF files are supported.');
                            return;
                          }
                          if (file.size > 5 * 1024 * 1024) {
                            setErrorMsg('File exceeds 5MB limit.');
                            return;
                          }
                          setErrorMsg('');
                          setSelectedFile(file);
                        }
                      }}
                    />
                  </label>
                </div>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Resume Title / Version</label>
                <input
                  type="text"
                  value={resumeTitle}
                  onChange={(e) => setResumeTitle(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="e.g. Software Engineer Resume 2026"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Target Category</label>
                <select
                  value={resumeCategory}
                  onChange={(e) => setResumeCategory(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                >
                  <option value="General">General</option>
                  <option value="Software Engineer">Software Engineer</option>
                  <option value="Frontend Developer">Frontend Developer</option>
                  <option value="Backend Developer">Backend Developer</option>
                  <option value="Full Stack">Full Stack</option>
                  <option value="Data & AI">Data & AI</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Step 6: Career Preferences & Summary */}
        {step === 6 && (
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#0f172a', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <Compass size={18} color="#4f46e5" /> Career Preferences & Summary
            </h3>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 20 }}>Tailor your job search intent and professional pitch.</p>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 4 }}>Preferred Roles</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                {career.preferredRoles.map((role) => (
                  <span
                    key={role}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 6, background: '#f1f5f9', fontSize: 12 }}
                  >
                    {role}
                    <button type="button" onClick={() => removeCareerTag('preferredRoles', role)} style={{ border: 'none', background: 'none', cursor: 'pointer' }}>×</button>
                  </span>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  type="text"
                  placeholder="Add role (e.g. Backend Engineer)"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      addCareerTag('preferredRoles', (e.target as HTMLInputElement).value);
                      (e.target as HTMLInputElement).value = '';
                    }
                  }}
                  style={{ flex: 1, padding: '7px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Work Mode</label>
                <select
                  value={career.workModes[0] || 'Remote'}
                  onChange={(e) => setCareer({ ...career, workModes: [e.target.value] })}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                >
                  <option value="Remote">Remote</option>
                  <option value="Hybrid">Hybrid</option>
                  <option value="On-site">On-site</option>
                  <option value="Any">Flexible</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Availability</label>
                <input
                  type="text"
                  value={career.availability}
                  onChange={(e) => setCareer({ ...career, availability: e.target.value })}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13 }}
                  placeholder="e.g. Immediate / 2 Weeks"
                />
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Career Objective</label>
              <textarea
                rows={2}
                value={career.careerObjective}
                onChange={(e) => setCareer({ ...career, careerObjective: e.target.value })}
                style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13, resize: 'vertical' }}
                placeholder="What are your immediate professional goals?"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#475569', marginBottom: 4 }}>Professional Summary</label>
              <textarea
                rows={3}
                value={career.professionalSummary}
                onChange={(e) => setCareer({ ...career, professionalSummary: e.target.value })}
                style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: 13, resize: 'vertical' }}
                placeholder="A compelling 2-3 sentence summary of your background, strengths, and achievements."
              />
            </div>
          </div>
        )}

        {/* Step 7: Review & Finalize */}
        {step === 7 && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#ecfdf5', color: '#10b981', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px' }}>
                <CheckCircle size={32} />
              </div>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a' }}>You are ready to launch!</h3>
              <p style={{ fontSize: 13, color: '#64748b' }}>Review your profile summary below before activating your assistant.</p>
            </div>

            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10, padding: 20, marginBottom: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 14 }}>
                <div>
                  <span style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>Full Name</span>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#0f172a' }}>
                    {personal.fullName || `${personal.firstName} ${personal.lastName}`.trim()}
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>Email</span>
                  <div style={{ fontSize: 14, fontWeight: 500, color: '#0f172a' }}>{personal.email}</div>
                </div>
                <div>
                  <span style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>Education</span>
                  <div style={{ fontSize: 14, fontWeight: 500, color: '#0f172a' }}>
                    {educationList[0]?.degree} • {educationList[0]?.institution || 'Institution'}
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>Resume</span>
                  <div style={{ fontSize: 14, fontWeight: 500, color: '#0f172a' }}>
                    {selectedFile ? selectedFile.name : 'Skipped for now'}
                  </div>
                </div>
              </div>

              <div>
                <span style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>Skills Included</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {[...skills.programmingLanguages, ...skills.frameworks, ...skills.cloud].slice(0, 8).map(s => (
                    <span key={s} className="tag-badge tag-badge-primary">{s}</span>
                  ))}
                  {skills.programmingLanguages.length > 8 && <span className="tag-badge">+{skills.programmingLanguages.length - 8} more</span>}
                </div>
              </div>
            </div>

            <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, padding: 14, display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: '#1e40af' }}>
              <Sparkles size={18} />
              <span>
                Your profile will be securely saved to MongoDB and immediately available for form field auto-detection and AI-powered personalized question answering.
              </span>
            </div>
          </div>
        )}

        {/* Wizard Footer Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 28, paddingTop: 18, borderTop: '1px solid #f1f5f9' }}>
          <div>
            {step > 1 ? (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleBack}
                disabled={saving}
              >
                <ChevronLeft size={16} /> Back
              </button>
            ) : onCancel ? (
              <button type="button" className="btn btn-secondary" onClick={onCancel}>
                Cancel
              </button>
            ) : <div />}
          </div>

          <div>
            {step < 7 ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleNext}
              >
                Next <ChevronRight size={16} />
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleFinalSubmit}
                disabled={saving}
                style={{ background: '#10b981' }}
              >
                {saving ? 'Saving Profile...' : 'Complete Setup & Open Dashboard'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};


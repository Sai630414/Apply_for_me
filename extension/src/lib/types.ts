export interface User {
  _id: string;
  email: string;
  name: string;
  picture?: string;
  googleId?: string;
  createdAt?: string;
  updatedAt?: string;
  lastLoginAt?: string;
}

export interface PersonalInformation {
  firstName: string;
  lastName: string;
  fullName: string;
  email: string;
  phone: string;
  city: string;
  state: string;
  country: string;
  address: string;
  dateOfBirth: string;
  gender?: string | null;
  linkedin: string;
  github: string;
  portfolio: string;
}

export interface EducationItem {
  id?: string;
  institution: string;
  college?: string; // alias
  degree: string;
  specialization: string;
  branch?: string; // alias
  department?: string;
  startYear?: string;
  graduationYear: string;
  currentAcademicYear?: string;
  currentYear?: string | null;
  cgpa: string;
  gradingSystem?: string;
  tenthPercentage?: string;
  twelfthPercentage?: string;
  backlogs?: string;
}

export interface Skills {
  programmingLanguages: string[];
  frameworks: string[];
  databases: string[];
  cloud: string[];
  cloudPlatforms?: string[]; // alias
  devops: string[];
  aiMl: string[];
  tools: string[];
  softSkills: string[];
  technicalSkills?: string[]; // alias
}

export interface ExperienceItem {
  id?: string;
  company: string;
  role: string;
  title?: string; // alias
  employmentType?: string; // Full-time, Internship, Freelance, Part-time
  startDate: string;
  endDate?: string;
  currentlyWorking?: boolean;
  duration?: string;
  responsibilities?: string;
  achievements?: string;
  technologies: string[];
  description: string;
}

export interface ProjectItem {
  id?: string;
  projectName: string;
  description: string;
  technologies: string[];
  githubUrl?: string;
  liveUrl?: string;
  projectUrl?: string | null; // alias
  role?: string;
  startDate?: string;
  endDate?: string;
}

export interface ProfessionalLinks {
  linkedin: string;
  github: string;
  portfolio: string;
}

export interface CareerPreferences {
  preferredRoles: string[];
  preferredIndustries: string[];
  employmentTypes: string[]; // Internship, Full-time, Part-time
  workModes: string[]; // Remote, Hybrid, On-site
  preferredLocations: string[];
  willingToRelocate: boolean;
  availability: string;
  careerObjective: string;
  careerObjectives?: string; // alias
  professionalSummary: string;
  expectedSalary?: string;
  workAuthorization?: string;
  sponsorshipRequired?: boolean;
}

export interface ApplicantProfile {
  _id?: string;
  userId: string;
  personalInformation: PersonalInformation;
  education: EducationItem[];
  skills: Skills;
  experiences: ExperienceItem[];
  projects: ProjectItem[];
  professionalLinks: ProfessionalLinks;
  careerPreferences: CareerPreferences;
  onboardingCompleted?: boolean;
  completionPercentage: number;
  updatedAt: string;
  createdAt?: string;
}

export interface ProfileCompletionDetails {
  completionPercentage: number;
  missingRequired: string[];
  suggestions: string[];
  hasProfile?: boolean;
}

export type ApplicationStatus = 'Draft' | 'Applied' | 'Interview' | 'Rejected' | 'Selected';

export interface ApplicationRecord {
  _id?: string;
  userId: string;
  companyName: string;
  jobTitle: string;
  jobUrl?: string;
  resumeId?: string;
  status: ApplicationStatus;
  notes?: string;
  appliedAt: string;
}

export interface ResumeMetadata {
  _id: string;
  userId: string;
  title: string;
  fileName: string;
  fileUrl: string;
  contentType: string;
  category?: string;
  fileSize?: number;
  isDefault?: boolean;
  uploadedAt: string;
}

export interface FormFieldDescriptor {
  elementId?: string;
  name?: string;
  selector?: string;
  type: string;
  label?: string;
  placeholder?: string;
  ariaLabel?: string;
  autocomplete?: string;
  options?: string[];
  currentValue?: string;
}

export type FieldCategory =
  | 'DIRECT_PROFILE_MAPPING'
  | 'DIRECT_PROFILE_FIELD'
  | 'AI_GENERATED_ANSWER'
  | 'USER_CONFIRMATION_REQUIRED'
  | 'USER_INPUT_REQUIRED'
  | 'FILE_UPLOAD'
  | 'CONSENT_OR_LEGAL'
  | 'UNSUPPORTED_FIELD'
  | 'UNSUPPORTED';

export interface FormFieldMapping {
  elementIdentifier: string;
  fieldName?: string;
  selector?: string;
  profileKey?: string | null;
  fillValue?: any;
  confidence: number;
  requiresReview: boolean;
  reason?: string | null;
  category?: FieldCategory;
  fieldType?: string;
  options?: string[];
  suggestedOptions?: string[];
  questionId?: string;
  questionCategory?: string;
  status?: string;

  // Section 12 structured response fields
  field_id?: string;
  question?: string;
  proposed_answer?: any;
  requires_confirmation?: boolean;
  confirmation_reason?: string | null;
  filled?: boolean;
}

export interface FormMappingRequest {
  url?: string;
  formTitle?: string;
  companyName?: string;
  jobTitle?: string;
  jobDescription?: string;
  fields: FormFieldDescriptor[];
}

export interface FormMappingResponse {
  mappings: FormFieldMapping[];
  totalFields: number;
  matchedFields: number;
  unmatchedFields: number;
  directMappedCount?: number;
  aiGeneratedCount?: number;
  userInputRequiredCount?: number;
  userConfirmationRequiredCount?: number;
  fileUploadCount?: number;
  consentLegalCount?: number;
  unsupportedCount?: number;
}

export interface FieldFillResult {
  name: string;
  elementIdentifier: string;
  selector?: string;
  status: 'filled' | 'skipped' | 'failed';
  reason?: string;
  value?: string;
  category?: FieldCategory;
}

export interface AutofillResult {
  success: boolean;
  totalDetected: number;
  totalMapped: number;
  totalFilled: number;
  skipped: number;
  failed: number;
  directMappedCount?: number;
  aiGeneratedCount?: number;
  userInputRequiredCount?: number;
  fields: FieldFillResult[];
  message: string;
}

export interface JobContext {
  companyName: string;
  jobTitle: string;
  jobDescription: string;
  url: string;
}

export interface AnswerGenerationRequest {
  question: string;
  companyName: string;
  jobTitle: string;
  jobDescription?: string;
  mode?: 'standard' | 'concise' | 'professional' | 'technical';
}

export interface AnswerGenerationResponse {
  question: string;
  companyName: string;
  jobTitle: string;
  answer: string;
  confidence: number;
  keyPointsUsed: string[];
  clarificationNeeded?: string | null;
}

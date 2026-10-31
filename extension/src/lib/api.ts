import { storage } from './storage';
import {
  User,
  ApplicantProfile,
  ProfileCompletionDetails,
  ApplicationRecord,
  ResumeMetadata,
  FormFieldDescriptor,
  FormMappingResponse,
  AnswerGenerationRequest,
  AnswerGenerationResponse
} from './types';

const DEFAULT_API_BASE = 'http://localhost:8000/api';

class ApiClient {
  private async getBaseUrl(): Promise<string> {
    const custom = await storage.get<string>('custom_api_url');
    return custom ? custom.replace(/\/+$/, '') : DEFAULT_API_BASE;
  }

  private async getAuthToken(): Promise<string | null> {
    return await storage.get<string>('auth_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const baseUrl = await this.getBaseUrl();
    const token = await this.getAuthToken();

    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string> || {}),
    };

    // Only set Content-Type to JSON if body is NOT FormData
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorBody = await response.text();
      let errorMsg = `HTTP ${response.status}`;
      try {
        const parsed = JSON.parse(errorBody);
        errorMsg = parsed.detail || errorMsg;
      } catch {}
      throw new Error(errorMsg);
    }

    return response.json();
  }

  // Authentication
  async devLogin(email: string, name: string): Promise<{ access_token: string; user: User }> {
    const data = await this.request<{ access_token: string; token_type: string; user: User }>(
      '/auth/dev-login',
      {
        method: 'POST',
        body: JSON.stringify({ email, name }),
      }
    );
    await storage.set('auth_token', data.access_token);
    await storage.set('current_user', data.user);
    return data;
  }

  async googleLogin(idToken: string): Promise<{ access_token: string; user: User }> {
    const data = await this.request<{ access_token: string; token_type: string; user: User }>(
      '/auth/google',
      {
        method: 'POST',
        body: JSON.stringify({ id_token: idToken }),
      }
    );
    await storage.set('auth_token', data.access_token);
    await storage.set('current_user', data.user);
    return data;
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  async logout(): Promise<void> {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } catch {}
    await storage.remove('auth_token');
    await storage.remove('current_user');
  }

  // Profile Management
  async getProfile(): Promise<ApplicantProfile> {
    return this.request<ApplicantProfile>('/profiles/me');
  }

  async createProfile(profile: Partial<ApplicantProfile>): Promise<ApplicantProfile> {
    return this.request<ApplicantProfile>('/profiles', {
      method: 'POST',
      body: JSON.stringify(profile),
    });
  }

  async updateProfile(profile: Partial<ApplicantProfile>): Promise<ApplicantProfile> {
    return this.request<ApplicantProfile>('/profiles/me', {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
  }

  async patchProfile(patch: Partial<ApplicantProfile>): Promise<ApplicantProfile> {
    return this.request<ApplicantProfile>('/profiles/me', {
      method: 'PATCH',
      body: JSON.stringify(patch),
    });
  }

  async saveProfile(profile: Partial<ApplicantProfile>): Promise<ApplicantProfile> {
    return this.updateProfile(profile);
  }

  async getProfileCompletion(): Promise<ProfileCompletionDetails> {
    return this.request<ProfileCompletionDetails>('/profiles/me/completion');
  }

  // Resumes
  async getResumes(): Promise<ResumeMetadata[]> {
    return this.request<ResumeMetadata[]>('/resumes');
  }

  async uploadResume(
    file: File,
    title: string = 'My Resume',
    category: string = 'General',
    isDefault: boolean = false
  ): Promise<ResumeMetadata> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('category', category);
    formData.append('isDefault', String(isDefault));

    return this.request<ResumeMetadata>('/resumes/upload', {
      method: 'POST',
      body: formData,
    });
  }

  async setDefaultResume(resumeId: string): Promise<ResumeMetadata> {
    return this.request<ResumeMetadata>(`/resumes/${resumeId}/default`, {
      method: 'PATCH',
    });
  }

  async deleteResume(resumeId: string): Promise<void> {
    await this.request(`/resumes/${resumeId}`, { method: 'DELETE' });
  }

  // Applications
  async getApplications(status?: string): Promise<ApplicationRecord[]> {
    const query = status ? `?status_filter=${status}` : '';
    return this.request<ApplicationRecord[]>(`/applications${query}`);
  }

  async saveApplication(app: Partial<ApplicationRecord>): Promise<ApplicationRecord> {
    return this.request<ApplicationRecord>('/applications', {
      method: 'POST',
      body: JSON.stringify(app),
    });
  }

  async updateApplication(id: string, app: Partial<ApplicationRecord>): Promise<ApplicationRecord> {
    return this.request<ApplicationRecord>(`/applications/${id}`, {
      method: 'PUT',
      body: JSON.stringify(app),
    });
  }

  // Autofill Engine Mapping
  async mapFormFields(
    fieldsOrPayload: FormFieldDescriptor[] | { fields: FormFieldDescriptor[]; companyName?: string; jobTitle?: string; jobDescription?: string; url?: string }
  ): Promise<FormMappingResponse> {
    const payload = Array.isArray(fieldsOrPayload)
      ? { fields: fieldsOrPayload }
      : fieldsOrPayload;

    return this.request<FormMappingResponse>('/autofill/map-fields', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // AI Generation
  async generateAnswer(payload: AnswerGenerationRequest): Promise<AnswerGenerationResponse> {
    return this.request<AnswerGenerationResponse>('/ai/generate-answer', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // Account Deletion
  async deleteAccount(): Promise<void> {
    await this.request('/users/me', { method: 'DELETE' });
    await this.logout();
  }
}

export const api = new ApiClient();

import { apiClient } from '../api';

export interface PackageMetadata {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  author_id: string;
  created_at: string;
  updated_at: string;
  tags: string[];
  subject: string;
  grade_level: string;
  language?: string;
  language_name?: string;
  country?: string;
  license: string;
  checksum: string;
}

export interface ExamSettings {
  shuffle_questions: boolean;
  shuffle_options: boolean;
  show_results_immediately: boolean;
  allow_review: boolean;
  require_seb: boolean;
  time_multiplier: number;
  passing_score: number;
}

export interface ExamTemplate {
  title: string;
  description: string;
  duration_minutes: number;
  instructions: string;
  settings: ExamSettings;
}

export interface QuestionVariable {
  name: string;
  type: 'integer' | 'float' | 'choice';
  min?: number;
  max?: number;
  step?: number;
  choices?: string[];
  formula?: string;
}

export interface QuestionTemplate {
  id: string;
  question_type: 'multiple_choice' | 'essay' | 'dynamic_math';
  text: string;
  options: string[] | null;
  correct_answer: string | null;
  rubric: string | null;
  points: number;
  variables: QuestionVariable[];
  tags: string[];
  difficulty: 'easy' | 'medium' | 'hard';
  estimated_time_minutes: number;
}

export interface RubricCriterion {
  id: string;
  description: string;
  points: number;
  keywords: string[];
}

export interface RubricTemplate {
  id: string;
  question_id: string;
  criteria: RubricCriterion[];
  total_points: number;
}

export interface TestPackage {
  metadata: PackageMetadata;
  exam: ExamTemplate;
  questions: QuestionTemplate[];
  rubrics: RubricTemplate[];
}

export interface PackageExportRequest {
  exam_id: string;
  include_answers: boolean;
  include_rubrics: boolean;
  include_variables: boolean;
  format: 'json' | 'yaml';
  compress: boolean;
  language?: string;
  language_name?: string;
  country?: string;
  subject?: string;
  grade_level?: string;
  save_to_server?: boolean;
}

export interface PackageImportResult {
  success: boolean;
  package_id: string | null;
  exam_id: string | null;
  questions_imported: number;
  rubrics_imported: number;
  errors: string[];
  warnings: string[];
}

export interface PackageValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface PackageListResponse {
  packages: PackageMetadata[];
}

export interface CurriculumModuleSummary {
  id: string;
  name: string;
  description: string;
  country: string;
  language: string;
  language_name: string;
  grade_level: string;
  subject: string;
  curriculum: string;
  question_count: number;
  duration_minutes: number;
  total_points: number;
  randomizer_enabled: boolean;
  path: string;
}

export interface CurriculumBrowseResponse {
  total: number;
  offset: number;
  limit: number;
  countries: string[];
  languages: { code: string; name: string }[];
  grades: string[];
  subjects: string[];
  modules: CurriculumModuleSummary[];
}

export const MODULE_LANGUAGES: { code: string; name: string; defaultCountry: string }[] = [
  { code: 'en', name: 'English', defaultCountry: 'usa' },
  { code: 'hu', name: 'Magyar', defaultCountry: 'hungary' },
  { code: 'de', name: 'Deutsch', defaultCountry: 'germany' },
  { code: 'fr', name: 'Français', defaultCountry: 'france' },
  { code: 'es', name: 'Español', defaultCountry: 'spain' },
  { code: 'it', name: 'Italiano', defaultCountry: 'italy' },
  { code: 'nl', name: 'Nederlands', defaultCountry: 'netherlands' },
  { code: 'pl', name: 'Polski', defaultCountry: 'poland' },
  { code: 'pt', name: 'Português', defaultCountry: 'portugal' },
  { code: 'pt-BR', name: 'Português (Brasil)', defaultCountry: 'brazil' },
  { code: 'sv', name: 'Svenska', defaultCountry: 'sweden' },
  { code: 'no', name: 'Norsk', defaultCountry: 'norway' },
  { code: 'da', name: 'Dansk', defaultCountry: 'denmark' },
  { code: 'fi', name: 'Suomi', defaultCountry: 'finland' },
  { code: 'uk', name: 'Українська', defaultCountry: 'ukraine' },
  { code: 'ja', name: '日本語', defaultCountry: 'japan' },
  { code: 'zh', name: '中文', defaultCountry: 'china' },
  { code: 'ar', name: 'العربية', defaultCountry: 'international' },
  { code: 'ko', name: '한국어', defaultCountry: 'south_korea' },
  { code: 'tr', name: 'Türkçe', defaultCountry: 'turkey' },
  { code: 'ro', name: 'Română', defaultCountry: 'romania' },
  { code: 'cs', name: 'Čeština', defaultCountry: 'czechia' },
  { code: 'sk', name: 'Slovenčina', defaultCountry: 'slovakia' },
  { code: 'el', name: 'Ελληνικά', defaultCountry: 'greece' },
  { code: 'bg', name: 'Български', defaultCountry: 'bulgaria' },
  { code: 'hr', name: 'Hrvatski', defaultCountry: 'croatia' },
  { code: 'et', name: 'Eesti', defaultCountry: 'estonia' },
  { code: 'ga', name: 'Gaeilge', defaultCountry: 'ireland' },
  { code: 'lv', name: 'Latviešu', defaultCountry: 'latvia' },
  { code: 'lt', name: 'Lietuvių', defaultCountry: 'lithuania' },
  { code: 'mt', name: 'Malti', defaultCountry: 'malta' },
  { code: 'sl', name: 'Slovenščina', defaultCountry: 'slovenia' },
];

export const packagesService = {
  async exportPackage(request: PackageExportRequest): Promise<{
    content: string | Blob;
    media_type: string;
    filename: string;
    saved_server_path?: string | null;
    language?: string;
    language_name?: string;
    country?: string;
  }> {
    const response = await apiClient.post('/packages/export', request);
    const data = response.data;
    const rawContent = typeof data?.content === 'string' ? data.content : JSON.stringify(data, null, 2);
    const mediaType = String(data?.media_type || (request.format === 'yaml' ? 'application/yaml' : 'application/json'));
    const filename = String(data?.filename || `package.${request.format}`);

    return {
      content: rawContent,
      media_type: mediaType,
      filename,
      saved_server_path: data?.saved_server_path || null,
      language: data?.language,
      language_name: data?.language_name,
      country: data?.country,
    };
  },

  async importPackage(
    file: File,
    options?: {
      language?: string;
      language_name?: string;
      country?: string;
      save_to_server?: boolean;
    }
  ): Promise<PackageImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.language) formData.append('language', options.language);
    if (options?.language_name) formData.append('language_name', options.language_name);
    if (options?.country) formData.append('country', options.country);
    if (options?.save_to_server !== undefined) {
      formData.append('save_to_server', String(options.save_to_server));
    }

    const response = await apiClient.post('/packages/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async validatePackage(file: File): Promise<PackageValidationResult> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/packages/validate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async listPackages(filters?: {
    subject?: string;
    grade_level?: string;
    tags?: string;
    author_id?: string;
  }): Promise<PackageListResponse> {
    const params = new URLSearchParams();
    if (filters?.subject) params.append('subject', filters.subject);
    if (filters?.grade_level) params.append('grade_level', filters.grade_level);
    if (filters?.tags) params.append('tags', filters.tags);
    if (filters?.author_id) params.append('author_id', filters.author_id);

    const response = await apiClient.get(`/packages?${params.toString()}`);
    return response.data;
  },

  async listCurriculumModules(filters?: {
    country?: string;
    language?: string;
    grade_level?: string;
    subject?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<CurriculumBrowseResponse> {
    const params = new URLSearchParams();
    if (filters?.country) params.append('country', filters.country);
    if (filters?.language) params.append('language', filters.language);
    if (filters?.grade_level) params.append('grade_level', filters.grade_level);
    if (filters?.subject) params.append('subject', filters.subject);
    if (filters?.search) params.append('search', filters.search);
    if (filters?.limit !== undefined) params.append('limit', String(filters.limit));
    if (filters?.offset !== undefined) params.append('offset', String(filters.offset));

    const response = await apiClient.get(`/packages/curriculum?${params.toString()}`);
    return response.data;
  },

  async importCurriculumModule(path: string): Promise<PackageImportResult> {
    const response = await apiClient.post('/packages/curriculum/import', { path });
    return response.data;
  },

  async importRepositoryPackage(packageId: string): Promise<PackageImportResult> {
    const response = await apiClient.post(`/packages/${packageId}/import`);
    return response.data;
  },

  async downloadPackage(packageId: string, format: 'json' | 'yaml' = 'json'): Promise<{
    content: Blob;
    media_type: string;
    filename: string;
  }> {
    const response = await apiClient.get(`/packages/${packageId}/download?format=${format}`);
    const data = response.data;
    const rawContent = typeof data?.content === 'string' ? data.content : JSON.stringify(data, null, 2);
    const mediaType = String(data?.media_type || 'application/json');
    const filename = String(data?.filename || `package.${format}`);

    return {
      content: new Blob([rawContent], { type: mediaType }),
      media_type: mediaType,
      filename,
    };
  },

  async publishPackage(packageId: string, isPublic: boolean = true): Promise<{
    status: string;
    message: string;
    package_id: string;
    is_public: boolean;
  }> {
    const formData = new FormData();
    formData.append('is_public', isPublic.toString());

    const response = await apiClient.post(`/packages/${packageId}/publish`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

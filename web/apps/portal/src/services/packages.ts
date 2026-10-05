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

export const packagesService = {
  async exportPackage(request: PackageExportRequest): Promise<{
    content: string | Blob;
    media_type: string;
    filename: string;
  }> {
    const response = await apiClient.post('/packages/export', request, {
      responseType: 'blob',
    });
    
    // Get filename from Content-Disposition header
    const contentDisposition = response.headers['content-disposition'];
    let filename = `package.${request.format}`;
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/);
      if (match) filename = match[1];
    }
    
    return {
      content: response.data,
      media_type: String(response.headers['content-type'] || 'application/json'),
      filename,
    };
  },

  async importPackage(file: File): Promise<PackageImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    
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

  async downloadPackage(packageId: string, format: 'json' | 'yaml' = 'json'): Promise<{
    content: Blob;
    media_type: string;
    filename: string;
  }> {
    const response = await apiClient.get(`/packages/${packageId}/download?format=${format}`, {
      responseType: 'blob',
    });
    
    const contentDisposition = response.headers['content-disposition'];
    let filename = `package.${format}`;
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/);
      if (match) filename = match[1];
    }
    
    return {
      content: response.data,
      media_type: String(response.headers['content-type'] || 'application/json'),
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

// Helper function to download blob as file
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

// Helper function to parse package file
export async function parsePackageFile(file: File): Promise<TestPackage> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        let pkg: TestPackage;
        
        if (file.name.endsWith('.gz')) {
          // For gzipped files, we'd need a decompression library
          // For now, reject with helpful message
          reject(new Error('Gzipped files not yet supported in browser. Please decompress first.'));
          return;
        }
        
        if (file.name.endsWith('.yaml') || file.name.endsWith('.yml')) {
          // Would need js-yaml library
          reject(new Error('YAML parsing not yet supported. Please use JSON format.'));
          return;
        }
        
        pkg = JSON.parse(content);
        resolve(pkg);
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });
}
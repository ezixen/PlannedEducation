/**
 * Test Package Service for PlannedEducation
 * Handles import/export of modular test packages (JSON/YAML)
 * Supports sharing test templates, rubrics, and question banks
 */

import { apiClient } from '../api';

export interface TestPackage {
  metadata: PackageMetadata;
  exam: ExamTemplate;
  questions: QuestionTemplate[];
  rubrics: RubricTemplate[];
}

export interface PackageMetadata {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  authorId: string;
  createdAt: string;
  updatedAt: string;
  tags: string[];
  subject: string;
  gradeLevel: string;
  license: string; // e.g., "CC-BY-4.0", "MIT", "Proprietary"
  checksum: string; // SHA-256 of package content
}

export interface ExamTemplate {
  title: string;
  description: string;
  duration_minutes: number;
  instructions: string;
  settings: ExamSettings;
}

export interface ExamSettings {
  shuffleQuestions: boolean;
  shuffleOptions: boolean;
  showResultsImmediately: boolean;
  allowReview: boolean;
  requireSEB: boolean;
  timeMultiplier: number;
  passingScore: number;
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
  estimatedTimeMinutes: number;
}

export interface QuestionVariable {
  name: string;
  type: 'integer' | 'float' | 'choice';
  min?: number;
  max?: number;
  step?: number;
  choices?: string[];
  formula?: string; // For computed variables
}

export interface RubricTemplate {
  id: string;
  questionId: string;
  criteria: RubricCriterion[];
  totalPoints: number;
}

export interface RubricCriterion {
  id: string;
  description: string;
  points: number;
  keywords: string[]; // For AI matching
}

export interface PackageExportOptions {
  includeAnswers: boolean;
  includeRubrics: boolean;
  includeVariables: boolean;
  format: 'json' | 'yaml';
  compress: boolean;
}

export interface PackageImportResult {
  success: boolean;
  packageId?: string;
  examId?: string;
  questionsImported: number;
  rubricsImported: number;
  errors: string[];
  warnings: string[];
}

class TestPackageService {
  /**
   * Export a test package from an existing exam
   */
  async exportPackage(
    examId: string,
    options: PackageExportOptions = {
      includeAnswers: true,
      includeRubrics: true,
      includeVariables: true,
      format: 'json',
      compress: false,
    }
  ): Promise<Blob> {
    // Fetch exam data
    const examResponse = await apiClient.get(`/exams/${examId}`);
    const exam = examResponse.data;
    
    // Fetch questions
    const questionsResponse = await apiClient.get(`/exams/${examId}/questions`);
    const questions = questionsResponse.data;
    
    // Build package
    const pkg: TestPackage = {
      metadata: {
        id: crypto.randomUUID(),
        name: exam.title,
        version: '1.0.0',
        description: exam.description || '',
        author: '', // Will be filled by backend
        authorId: '', // Will be filled by backend
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        tags: [],
        subject: '',
        gradeLevel: '',
        license: 'CC-BY-4.0',
        checksum: '',
      },
      exam: {
        title: exam.title,
        description: exam.description || '',
        duration_minutes: exam.duration_minutes,
        instructions: '',
        settings: {
          shuffleQuestions: false,
          shuffleOptions: false,
          showResultsImmediately: false,
          allowReview: true,
          requireSEB: !!exam.seb_config_key,
          timeMultiplier: 1.0,
          passingScore: 60,
        },
      },
      questions: questions.map((q: any) => ({
        id: q.id,
        question_type: q.question_type,
        text: q.text,
        options: q.options_json ? JSON.parse(q.options_json) : null,
        correct_answer: options.includeAnswers ? q.correct_answer : null,
        rubric: options.includeRubrics ? q.rubric : null,
        points: q.points,
        variables: [],
        tags: [],
        difficulty: 'medium',
        estimatedTimeMinutes: 5,
      })),
      rubrics: [],
    };
    
    // Calculate checksum
    const content = JSON.stringify({ ...pkg, metadata: { ...pkg.metadata, checksum: '' } });
    const encoder = new TextEncoder();
    const data = encoder.encode(content);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    pkg.metadata.checksum = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    
    // Serialize
    let serialized: string;
    if (options.format === 'yaml') {
      serialized = this.toYAML(pkg);
    } else {
      serialized = JSON.stringify(pkg, null, 2);
    }
    
    // Compress if requested
    if (options.compress) {
      const stream = new CompressionStream('gzip');
      const writer = stream.writable.getWriter();
      const encoder = new TextEncoder();
      writer.write(encoder.encode(serialized));
      writer.close();
      
      const compressed = await new Response(stream.readable).blob();
      return compressed;
    }
    
    return new Blob([serialized], { type: options.format === 'yaml' ? 'application/yaml' : 'application/json' });
  }
  
  /**
   * Import a test package
   */
  async importPackage(file: File): Promise<PackageImportResult> {
    const formData = new FormData();
    formData.append('package', file);
    
    try {
      const response = await apiClient.post('/packages/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        questionsImported: 0,
        rubricsImported: 0,
        errors: [error.response?.data?.detail || error.message],
        warnings: [],
      };
    }
  }
  
  /**
   * Validate a package file
   */
  async validatePackage(file: File): Promise<{ valid: boolean; errors: string[]; warnings: string[] }> {
    const formData = new FormData();
    formData.append('package', file);
    
    try {
      const response = await apiClient.post('/packages/validate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    } catch (error: any) {
      return {
        valid: false,
        errors: [error.response?.data?.detail || error.message],
        warnings: [],
      };
    }
  }
  
  /**
   * List available packages (from marketplace or local)
   */
  async listPackages(filters?: {
    subject?: string;
    gradeLevel?: string;
    tags?: string[];
    authorId?: string;
  }): Promise<PackageMetadata[]> {
    const params = new URLSearchParams();
    if (filters?.subject) params.append('subject', filters.subject);
    if (filters?.gradeLevel) params.append('gradeLevel', filters.gradeLevel);
    if (filters?.tags) filters.tags.forEach(t => params.append('tags', t));
    if (filters?.authorId) params.append('authorId', filters.authorId);
    
    const response = await apiClient.get(`/packages?${params.toString()}`);
    return response.data;
  }
  
  /**
   * Download a package by ID
   */
  async downloadPackage(packageId: string, format: 'json' | 'yaml' = 'json'): Promise<Blob> {
    const response = await apiClient.get(`/packages/${packageId}/download`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  }
  
  /**
   * Publish a package to the marketplace
   */
  async publishPackage(packageId: string, isPublic: boolean = true): Promise<void> {
    await apiClient.post(`/packages/${packageId}/publish`, { is_public: isPublic });
  }
  
  /**
   * Convert object to YAML string
   */
  private toYAML(obj: any): string {
    
    function stringify(value: any, indent: number = 0): string {
      const spaces = '  '.repeat(indent);
      
      if (value === null) return 'null';
      if (typeof value === 'string') return `"${value.replace(/"/g, '\\"')}"`;
      if (typeof value === 'number' || typeof value === 'boolean') return String(value);
      if (Array.isArray(value)) {
        if (value.length === 0) return '[]';
        return '\n' + value.map(v => `${spaces}  - ${stringify(v, indent + 1)}`).join('\n');
      }
      if (typeof value === 'object') {
        const keys = Object.keys(value);
        if (keys.length === 0) return '{}';
        return '\n' + keys.map(k => `${spaces}  ${k}: ${stringify(value[k], indent + 1)}`).join('\n');
      }
      return String(value);
    }
    
    function process(obj: any, indent: number = 0): string[] {
      const result: string[] = [];
      const spaces = '  '.repeat(indent);
      
      for (const [key, value] of Object.entries(obj)) {
        if (Array.isArray(value)) {
          if (value.length === 0) {
            result.push(`${spaces}${key}: []`);
          } else if (typeof value[0] === 'object') {
            result.push(`${spaces}${key}:`);
            value.forEach(item => {
              result.push(`${spaces}  -`);
              result.push(...process(item, indent + 2).map(l => `${spaces}    ${l.trimStart()}`));
            });
          } else {
            result.push(`${spaces}${key}: [${value.map(v => stringify(v)).join(', ')}]`);
          }
        } else if (typeof value === 'object' && value !== null) {
          result.push(`${spaces}${key}:`);
          result.push(...process(value, indent + 1));
        } else {
          result.push(`${spaces}${key}: ${stringify(value)}`);
        }
      }
      return result;
    }
    
    return process(obj).join('\n');
  }
}

export const testPackageService = new TestPackageService();
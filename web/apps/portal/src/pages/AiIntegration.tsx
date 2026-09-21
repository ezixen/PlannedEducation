import { useAuth } from '../contexts/AuthContext';
import { API_URL } from '../api';

export function AiIntegration() {
  const { user } = useAuth();
  
  if (!user || user.role !== 'teacher') return <div>Unauthorized</div>;

  const systemPrompt = `You are an expert, objective teacher and AI grader working for the PlannedEducation platform. Your job is to assist teachers in grading exams, grouping mistakes, and transcribing handwritten math or audio feedback. You must be strictly objective, unbiased, and format your output cleanly. You are processing anonymized data to protect student privacy.`;

  return (
    <div>
      <h1>External AI Integrations</h1>
      <p style={{ color: 'gray', marginBottom: '2rem' }}>
        PlannedEducation does not process AI natively to ensure 100% data sovereignty. 
        Instead, we provide a secure, anonymized API endpoint that you (or an external script/service) can plug into any LLM.
      </p>

      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '2rem' }}>
        <h3>Your Anonymized API Endpoint</h3>
        <p>Use this endpoint to pull student submissions. <strong>All names, emails, and IDs are automatically stripped.</strong></p>
        <code style={{ display: 'block', padding: '1rem', backgroundColor: '#000', color: '#10b981', borderRadius: '4px', marginBottom: '1rem' }}>
          GET {API_URL}/anonymizer/exams/&#123;exam_id&#125;/submissions
        </code>
        <p>Use this endpoint for the AI to push graded results back:</p>
        <code style={{ display: 'block', padding: '1rem', backgroundColor: '#000', color: '#10b981', borderRadius: '4px' }}>
          POST {API_URL}/anonymizer/submissions/&#123;submission_id&#125;/grades
        </code>
      </div>

      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '2rem' }}>
        <h3>Required System Prompt</h3>
        <p>When hooking our API up to an external LLM, you must supply this exact System Prompt so the AI understands its job, what to expect, and why it is receiving anonymized data:</p>
        <blockquote style={{ borderLeft: '4px solid var(--primary-color)', paddingLeft: '1rem', fontStyle: 'italic', color: 'gray' }}>
          "{systemPrompt}"
        </blockquote>
      </div>

      <h3>Recommended External AI Providers</h3>
      <div style={{ display: 'grid', gap: '1rem', marginTop: '1rem' }}>
        
        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#3b82f6' }}>1. Google Gemini (Recommended Free Tier)</h4>
          <p style={{ fontSize: '0.9rem', margin: 0 }}>Offers extremely generous free tiers for `gemini-2.5-flash`. Highly recommended for large batches of text or image OCR.</p>
        </div>

        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#10b981' }}>2. Ollama (100% Free & Local)</h4>
          <p style={{ fontSize: '0.9rem', margin: 0 }}>Run models like Llama-3 or Mistral directly on your own computer. Zero cost, infinite usage, and maximum privacy.</p>
        </div>

        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#f59e0b' }}>3. OpenRouter (Free & Paid Models)</h4>
          <p style={{ fontSize: '0.9rem', margin: 0 }}>A unified API that gives you access to hundreds of models. They offer completely free limited tiers for certain models (like Meta Llama 3 8B), as well as paid access to GPT-4o or Claude 3.5 Sonnet.</p>
        </div>

        <div style={{ padding: '1rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#ef4444' }}>4. OpenAI (Paid)</h4>
          <p style={{ fontSize: '0.9rem', margin: 0 }}>Industry standard, but strictly pay-per-token. Best for complex reasoning tasks if you have budget.</p>
        </div>

      </div>
    </div>
  );
}

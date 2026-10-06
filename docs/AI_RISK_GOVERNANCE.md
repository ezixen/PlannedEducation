# AI Risk Governance for PlannedEducation

**Alignment**: NIST AI RMF 1.0 + Generative AI Profile (NIST-AI-600-1)
**Status**: Living document — update as AI capabilities evolve
**Last Updated**: 2026-10-06

---

## 1. Context: External AI Only Architecture

PlannedEducation **does not host or run any AI models internally**. The platform provides:

- **API Gateway** — Routes teacher requests to their chosen AI provider
- **Abstraction Layer** — Normalizes requests/responses across providers
- **Security Controls** — Input validation, output validation, rate limiting, audit logging
- **Teacher BYOK** — Teachers provide their own API keys (encrypted at rest)

**Supported Provider Types**:
- Google Gemini API
- Anthropic Claude API
- OpenAI API
- OpenRouter (multi-provider gateway)
- Local Ollama (self-hosted)
- Any OpenAI-compatible endpoint

---

## 2. NIST AI RMF 1.0 Function Mapping

### GOVERN (GV) — Organizational Governance

| Sub-function | Implementation |
|---|---|
| **GV-1** Policies & procedures | This document + `PLANS_UPDATED.md` Phase 7 |
| **GV-2** Roles & responsibilities | Teacher = AI output approver; Platform = infrastructure provider |
| **GV-3** Workforce competency | Teacher training on AI limitations (documentation) |
| **GV-4** Risk management culture | Transparent AI use, opt-in only, teacher approval required |

### MAP (MP) — Context & Risk Identification

| Sub-function | Implementation |
|---|---|
| **MP-1** Intended purpose | AI-assisted grading, test creation, content generation for education |
| **MP-2** Risk identification | See Section 3: Risk Catalog |
| **MP-3** Risk assessment | Likelihood × Impact matrix per risk |
| **MP-4** Risk prioritization | High: PII leakage, hallucinated grades; Medium: Cost overruns, bias |

### MEASURE (MS) — Risk Measurement

| Sub-function | Implementation |
|---|---|
| **MS-1** Metrics & monitoring | AI call latency, error rates, token usage, cost per teacher |
| **MS-2** Testing & evaluation | Output schema validation, hallucination detection, bias sampling |
| **MS-3** Independent assessment | Teacher review workflow (human-in-the-loop) |

### MANAGE (MA) — Risk Treatment

| Sub-function | Implementation |
|---|---|
| **MA-1** Risk treatment | Mitigation controls per Section 4 |
| **MA-2** Residual risk acceptance | Documented per teacher per feature |
| **MA-3** Continuous improvement | Quarterly risk review, incident-driven updates |

---

## 3. Risk Catalog (Generative AI Profile)

| ID | Risk | Likelihood | Impact | Category |
|---|---|---|---|---|
| **R-01** | **Prompt Injection** — Malicious input alters AI behavior | Medium | High | Security |
| **R-02** | **Hallucinated Grades** — AI invents scores/feedback | Medium | High | Quality/Safety |
| **R-03** | **PII Leakage** — Student data sent to AI provider | Low (anonymizer) | Critical | Privacy |
| **R-04** | **Bias in Grading** — Systematic unfairness across demographics | Medium | High | Fairness |
| **R-05** | **Cost Overrun** — Teacher exceeds budget | Medium | Medium | Economic |
| **R-06** | **Provider Outage** — AI service unavailable during grading | Low | Medium | Availability |
| **R-07** | **Model Drift** — Provider updates change behavior silently | Low | Medium | Reliability |
| **R-08** | **Output Format Violation** — AI returns invalid JSON/schema | Medium | Medium | Integrity |
| **R-09** | **Over-reliance** — Teachers skip review of AI suggestions | Medium | High | Human Factors |
| **R-10** | **Supply Chain** — Compromised provider or model | Low | Critical | Supply Chain |

---

## 4. Mitigation Controls (Per Risk)

### R-01: Prompt Injection
- **Input Sanitization**: Strip/escape control characters, limit prompt length
- **System Prompt Hardening**: Explicit instructions to ignore injection attempts
- **Allow-list Validation**: Only permitted prompt templates for grading/test creation
- **Audit Log**: All prompts/responses logged with teacher ID, timestamp

### R-02: Hallucinated Grades
- **Output Schema Validation**: JSON Schema enforcement on AI responses
- **Confidence Scoring**: Require AI to return confidence; flag < 0.8 for review
- **Teacher Approval Required**: No auto-apply; teacher must review each AI grade
- **Cross-check**: Compare AI grade with rubric/answer key where available
- **Fallback**: Manual grading always available

### R-03: PII Leakage
- **Anonymizer Pipeline**: All student identifiers replaced with `Student_1`, `Student_2`...
- **Presidio PII Scrubber**: Microsoft Presidio (MIT licensed) on essay content
- **Data Minimization**: Only send necessary content (no metadata, no names)
- **Provider Contracts**: Document data handling per provider (no training on data)

### R-04: Bias in Grading
- **Diverse Prompt Templates**: Test prompts across demographic representations
- **Bias Sampling**: Periodic manual audit of AI grades vs. human grades by demographic
- **Rubric Anchoring**: AI grades anchored to explicit rubric criteria
- **Appeal Process**: Students can request human re-grade

### R-05: Cost Overrun
- **Per-Teacher Budgets**: Monthly token/cost limits configurable by teacher
- **Real-time Tracking**: Token usage displayed in Settings page
- **Hard Limits**: API calls blocked when budget exceeded
- **Alerts**: Email at 80%, 95%, 100% of budget

### R-06: Provider Outage
- **Multi-Provider Support**: Teacher can configure fallback providers
- **Graceful Degradation**: Queue requests, notify teacher, allow manual grading
- **Caching**: Cache repeated requests (e.g., same rubric + similar answers)

### R-07: Model Drift
- **Version Pinning**: Teacher selects specific model version (e.g., `gemini-1.5-pro-001`)
- **Regression Tests**: Automated test suite runs weekly against saved prompts
- **Change Detection**: Alert if output distribution shifts significantly

### R-08: Output Format Violation
- **Strict JSON Schema**: All AI endpoints enforce response schema
- **Retry with Correction**: Up to 2 retries with format error feedback
- **Fallback Parser**: Lenient parser for common format errors
- **Dead Letter Queue**: Failed parses logged for analysis

### R-09: Over-reliance
- **UI Design**: AI suggestions visually distinct from final grades
- **Mandatory Review**: "Approve" button required; no bulk auto-approve
- **Training Prompts**: In-app guidance on AI limitations
- **Audit Trail**: Track approval time, edits made by teacher

### R-10: Supply Chain
- **Provider Vetting**: Document security practices per supported provider
- **Dependency Scanning**: `pip-audit`/`npm audit` for AI SDKs
- **Incident Response**: Provider outage/compromise playbook

---

## 5. Generative AI Profile (NIST-AI-600-1) Specific Controls

### 5.1 Input Controls
- **Prompt Templates**: Pre-defined, versioned templates for each use case
- **Parameter Validation**: Temperature, max_tokens, top_p within safe ranges
- **Content Filtering**: Block requests containing prohibited content

### 5.2 Output Controls
- **Schema Validation**: JSON Schema for every AI response type
- **Hallucination Detection**: 
  - Consistency check (same input → similar output)
  - Fact-checking against rubric/answer key
  - Confidence threshold enforcement
- **Format Enforcement**: Structured output (JSON) only; no free-text grades

### 5.3 Monitoring & Observability
- **Metrics Collected**:
  - Latency (p50, p95, p99)
  - Token usage (input/output per call)
  - Error rate by type (validation, provider, timeout)
  - Cost per teacher per month
  - Teacher edit rate on AI suggestions
- **Alerting**:
  - Error rate > 5% for 5 minutes
  - Cost > 80% budget
  - Latency p95 > 30s
  - Hallucination detection rate > 10%

### 5.4 Human-in-the-Loop
- **Mandatory Review**: Every AI grade requires teacher approval
- **Edit Tracking**: Log all teacher modifications to AI output
- **Feedback Loop**: Teacher corrections fed back to improve prompts
- **Override Authority**: Teacher can always discard AI suggestion

---

## 6. Teacher-Facing Controls

### Settings Page (Per Teacher)
- **Provider Selection**: Choose from supported providers
- **Model Selection**: Pin specific model version
- **Budget Limits**: Monthly token/cost ceiling
- **Feature Toggles**: Enable/disable grading, test creation, content generation
- **Fallback Provider**: Optional secondary provider
- **Data Retention**: Auto-delete AI logs after N days (default 90)

### Transparency
- **Per-Call Logging**: Teacher can view their AI call history
- **Cost Dashboard**: Real-time token usage and estimated cost
- **Provider Status**: Green/yellow/red indicator per provider

---

## 7. Incident Response for AI

| Scenario | Response |
|---|---|
| **Hallucinated grade deployed** | Immediate revert, teacher notification, student appeal process |
| **PII leakage detected** | Provider notification, data deletion request, teacher/student notification |
| **Provider compromise** | Disable provider, rotate keys, migrate to fallback |
| **Bias detected** | Disable affected feature, manual audit, model/prompt adjustment |
| **Cost runaway** | Hard block at limit, teacher notification, budget reset option |

---

## 8. Compliance Mapping

| Standard | Requirement | Implementation |
|---|---|---|
| **NIST AI RMF 1.0** | All 4 functions | Sections 2-4 |
| **NIST-AI-600-1** | Generative AI Profile | Section 5 |
| **OWASP Top 10:2025 A03** | Supply Chain | Provider vetting, dependency scanning |
| **OWASP Top 10:2025 A08** | Integrity | Output validation, signed artifacts |
| **EU AI Act** (prep) | High-risk AI system | Education = high-risk; transparency, human oversight, logging |
| **FERPA/COPPA** | Student privacy | Anonymizer, no PII to AI, data minimization |

---

## 9. Future Enhancements

- [ ] **Red Teaming**: Automated adversarial prompt testing
- [ ] **Model Cards**: Documentation per supported model
- [ ] **Explainability**: Feature attribution for AI grades
- [ ] **Federated Evaluation**: Cross-institution bias benchmarking
- [ ] **Watermarking**: Detect AI-generated content in submissions

---

## 10. References

- NIST AI RMF 1.0: https://doi.org/10.6028/NIST.AI.100-1
- NIST AI RMF Generative AI Profile: https://doi.org/10.6028/NIST.AI.600-1
- NIST AI RMF Playbook: https://airc.nist.gov/AI_RMF_Knowledge_Base/Playbook
- OWASP Top 10:2025: https://top10.owasp.org/2025/
- OWASP LLM Top 10: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Microsoft Presidio: https://github.com/microsoft/presidio
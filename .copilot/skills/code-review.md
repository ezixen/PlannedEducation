---
name: code-reviewer-pro
description: Professional 10-section code, architecture, security (OWASP ASVS 5.0.0 & Top 10:2025), modern web standards, and performance review skill across any programming language (Python, TypeScript, JavaScript, React, HTML/CSS, SQL, Go, Rust, C/C++, C#, Java, Kotlin, Swift, Bash, PowerShell). Use when asked to review code, audit code quality, find bugs, perform security analysis, check modularity, optimize performance, or refactor code.
---

# Code Reviewer Pro 🔍🛡️

Perform rigorous, objective, evidence-based code and architecture reviews following the structured 10-section framework below. Integrates **OWASP ASVS 5.0.0**, **OWASP Top 10:2025**, **NIST SP 800-218 (SSDF)**, **Google Modern Web Guidance**, and **Modular Architecture Standards**.

---

## 🔄 Review Execution Process

1. **Context & Structure Discovery**: Read all target files carefully. When reviewing a feature or repository, inspect the surrounding module boundaries, schemas, and tests first.
2. **Complete 10-Section Audit**: Execute all 10 sections in order without skipping.
3. **Evidence-Based Findings**: Cite exact file paths, line ranges (`file.py#L10-L25`), and concrete code evidence for every finding. Never invent hypothetical problems unsupported by the code.
4. **Preserve Functionality**: Do not propose changes that break existing APIs or intended behavior unless the behavior itself is a bug or security vulnerability.
5. **Cross-Skill Synergy**:
   - For frontend/HTML/CSS/React reviews, cross-check against [`webdesign-and-modern-web/guides/`](./webdesign-and-modern-web/guides).
   - For security/auth/crypto reviews, cross-check against [`how2/MASTER_FROM_0_TO_HERO_UNIVERSAL_KB_2026.md`](./how2/MASTER_FROM_0_TO_HERO_UNIVERSAL_KB_2026.md) and [`how2/PDFs/OWASP_ASVS_5.0.0_en.pdf`](./how2/PDFs/OWASP_ASVS_5.0.0_en.pdf).

---

## 📋 The 10-Section Review Structure

### 1. Executive Summary
Provide a concise architectural overview covering:
- **Purpose**: What the module, component, or changeset accomplishes.
- **Overall Health**: High-level assessment of readiness and reliability.
- **Key Strengths**: Well-designed patterns, clean abstractions, or strong test coverage.
- **Primary Risks**: Top critical defects, security gaps, or architectural bottlenecks.

---

### 2. Code Quality & Architecture Scorecard

Rate each dimension from **1 to 10** with specific evidence from the codebase:

| Dimension | Score (1–10) | Key Evidence & Notes |
|:---|:---:|:---|
| **Readability & Clarity** | X/10 | Naming precision, self-documenting structure, cognitive load |
| **Modularity & File Size** | X/10 | Single responsibility, logical seams ($\le 400$ lines preferred; flag $>800$ line god-files) |
| **Performance & CWV** | X/10 | Algorithmic efficiency, query optimization, rendering/LCP/INP impact |
| **Security & Privacy** | X/10 | OWASP ASVS 5.0.0, auth boundaries, crypto hygiene, PII protection |
| **Maintainability & Tests** | X/10 | Type safety, error handling, testability, DRY/SOLID adherence |
| **Overall Weighted Score** | **X/10** | **Summary verdict (Ready / Needs Minor Fixes / Requires Refactor)** |

---

### 3. Bugs, Logic Defects & Concurrency Hazards

Inspect line-by-line for runtime and logical defects. If none exist, state: *"No functional bugs identified."*

- **Logic & Boundary Bugs**: Off-by-one errors, inverted conditions, unreachable branches, floating-point precision issues, timezone/UTC naive vs. aware datetime mismatches.
- **Null / Undefined / Optional Hazards**: Unchecked `None`/`null`/`undefined` dereferences, missing Pydantic/TypeScript optional guards.
- **Async & Concurrency Bugs**: Unawaited coroutines/promises, race conditions, deadlocks, synchronous blocking calls inside `async def` event loops, stale React closure state.
- **Resource & Memory Leaks**: Unclosed file handles, database sessions, WebSocket listeners, `setInterval` timers, or detached DOM nodes.
- **Error Handling Flaws**: Bare `except:` blocks swallowing critical exceptions, silent failures, or mismatched HTTP status codes.

*For each bug found, specify*: **Location (`file#Lxx`)** $\rightarrow$ **Root Cause** $\rightarrow$ **Runtime Impact** $\rightarrow$ **Exact Fix**.

---

### 4. Security, Privacy & Compliance Audit (OWASP ASVS 5.0.0)

Evaluate against modern 2026 security and privacy guardrails:

| Security Domain | Status (`Pass` / `Fail` / `N/A`) | Findings & Remediation |
|:---|:---:|:---|
| **Injection & SQL Safety** | Pass/Fail/N/A | Parameterized ORM queries only; zero string concatenation or f-strings in SQL/shell commands. |
| **Auth, Sessions & 2FA** | Pass/Fail/N/A | Bearer/httpOnly cookie validation, RBAC scope enforcement, Argon2id hashing, TOTP (RFC 6238) / WebAuthn Passkeys, rate limiting. |
| **Browser Token Storage** | Pass/Fail/N/A | No sensitive JWT access/refresh tokens or secrets persisted in `localStorage` (prefer `httpOnly` cookies or ephemeral memory/`sessionStorage`). |
| **Cryptography at Rest/Transit**| Pass/Fail/N/A | Fernet or Web Crypto AES-GCM for sensitive tokens; distinct keys for JWT signing vs. encryption; zero weak algorithms (MD5/SHA1/ECB). |
| **Secrets & Credentials** | Pass/Fail/N/A | Zero hardcoded API keys, passwords, or private keys in code, logs, or committed config. |
| **XSS, CSRF & CSP** | Pass/Fail/N/A | Output encoding, avoided `dangerouslySetInnerHTML`/`unsafe-eval`, strict Content Security Policy. |
| **SSRF & Path Traversal** | Pass/Fail/N/A | Validated URLs/webhooks, sanitized file paths (`Path.resolve()` containment checks). |
| **Privacy & PII (GDPR/FERPA)** | Pass/Fail/N/A | Zero student/user PII, passwords, or tokens in logs or error payloads; anonymization before external API calls. |
| **Free-Tier & Supply Chain** | Pass/Fail/N/A | Zero paid service lock-in; dependencies free of known CVEs (`pip-audit` / `npm audit`). |

**Overall Security Risk Level**: `None` | `Low` | `Medium` | `High` | `Critical`

---

### 5. Performance, Database & Frontend Web Vitals Review

Analyze both backend execution and frontend rendering efficiency:

- **Backend & Database**:
  - Algorithmic complexity ($\mathcal{O}(n^2)$ loops reducible to $\mathcal{O}(n)$ via hash maps/sets).
  - Database query efficiency: N+1 query elimination (`joinedload`/`selectinload`), missing composite indexes, pagination on large collections.
  - Async I/O: Offloading CPU-bound or synchronous I/O work (`asyncio.to_thread`) so the event loop never blocks.
- **Frontend & Modern Web Performance**:
  - Core Web Vitals: Largest Contentful Paint (`fetchpriority="high"`), Interaction to Next Paint (avoiding long main-thread tasks), Cumulative Layout Shift (`size-adjust` font fallbacks, explicit media dimensions).
  - Offscreen rendering deferral (`content-visibility: auto`) and code-splitting (`React.lazy` / dynamic `import()`).

---

### 6. Modularity, Modern Web Standards & Best Practices

Evaluate code organization and adherence to modern platform capabilities:

| Practice Area | Status | Evaluation Details |
|:---|:---:|:---|
| **File Size & Modularity** | Pass/Needs Work | Prefer $\le 400$ lines per file; split cohesive domains at logical seams (page shell vs. UI panel vs. custom hook vs. service module). |
| **Native Modern Web APIs** | Pass/Needs Work | Prefer native `<dialog>`, `popover="auto"`, CSS Anchor Positioning, `@container` queries, `:has()`, and View Transitions over heavy JS workarounds. |
| **Type Safety & Validation** | Pass/Needs Work | Strict TypeScript types (avoid `any`), Pydantic v2 schema validation (`Field` constraints, `ConfigDict`). |
| **UX & Error Presentation** | Pass/Needs Work | Inline contextual status/error cards near action buttons; human-friendly wording; `dd/mm/yyyy` dates; clean time formatting (`2m 15s`, no raw ms). |
| **Documentation Integrity** | Pass/Needs Work | Preserved docstrings and non-obvious architectural rationale; zero engineering/debug jargon leaked into user-facing UI strings. |
| **Testability & Hygiene** | Pass/Needs Work | Deterministic tests, zero orphaned background processes, automatic test artifact cleanup. |

---

### 7. Concrete Refactoring Suggestions (Before / After)

Provide high-impact, copy-pasteable refactorings ordered by priority (`[High]`, `[Medium]`, `[Low]`):

```markdown
**[High] [Concise Title of Refactoring]** (`path/to/file.ext#L10-L25`)

*Before:*
```python
# Problematic or suboptimal code
```

*After:*
```python
# Clean, secure, idiomatic replacement
```

*Rationale:* [1–2 sentences explaining the security, performance, or maintainability gain.]
```

---

### 8. Edge Cases & Fault Tolerance

Identify boundary conditions that require defensive handling:
- Empty collections, `null`/`None` payloads, whitespace-only strings, or extreme numeric boundaries (`0`, negative values, `MAX_SAFE_INTEGER`).
- Network timeouts, third-party API unavailability, or offline/airgapped school server operation.
- Concurrent duplicate requests (idempotency keys, `409 Conflict` handling, database transaction rollbacks).
- Unicode, RTL text, special characters in filenames/usernames, and high-contrast/reduced-motion accessibility preferences.

---

### 9. Prioritized Actionable Checklist

Provide a ready-to-execute task list grouped by urgency:

- **🔴 Critical / High Priority (Security, Data Integrity, Crashes)**
  - [ ] Fix item 1 (`file#Lxx`)
- **🟡 Medium Priority (Performance, Modularity, Edge Cases)**
  - [ ] Fix item 2 (`file#Lxx`)
- **🟢 Low Priority (Polish, Typing, Readability)**
  - [ ] Fix item 3 (`file#Lxx`)

---

### 10. Audit Report Persistence & Automated Remediation

1. **When Reviewing a Project or Module**:
   - Save a structured Markdown audit report in `plans/` (e.g., `plans/CODE_REVIEW_<MODULE>_<YYYYMMDD>.md`) containing sections 1–9 so any developer or agent can execute the fixes systematically.
2. **When Asked to Fix or Improve the Code Immediately**:
   - Apply the fixes directly using surgical file edits while preserving all existing functionality, public interfaces, and unrelated comments/docstrings.
   - Run the project's linter and test suite to verify 100% green status after applying the improvements.

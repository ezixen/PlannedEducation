# 🧠 Skills & Knowledge Base Master Library

Welcome to the central archive of **Google official skills, modern web design guidance, developer QA tools, and cybersecurity standards**. This library is structured so that both human contributors and autonomous AI coding agents (Antigravity, Gemini CLI, Claude, Copilot) can rapidly discover and execute the right tool for any task.

---

## 📁 Directory Structure Overview

```text
skills/
│
├── 🛠️ Root Developer & QA Skills (Deduplicated & Upgraded):
│   ├── universal-tester.md     # 🧪 Universal All-Tester & CI/CD Security Pro (universal-all-tester-pro): Logged pytest cache, frontend builds, OSS security scans, Trivy, CycloneDX SBOM, Cosign signing, SLSA, zero-orphan process hygiene
│   ├── code-review.md          # 🔍 Code Reviewer Pro (code-reviewer-pro): 10-section code, OWASP ASVS 5.0 & CWV audit
│   ├── web-search.md           # 🌐 Web Search Pro 2026 (web-search-pro-2026): Primary-source research, CVE & BLUF lookup
│   ├── fulltest.md             # 🧪 Full-Platform & Visual Tester Pro (full-platform-visual-qa-pro): Merged E2E + Playwright visual QA
│   └── cleanup-docs.md         # 🧹 Documentation Cleaner Pro (documentation-cleaner-pro): Dedup & ground-truth audit
│
├── 📚 Universal Knowledge Base & Security Standards:
│   └── how2/                   # 🛡️ NIST, OWASP, and RFC Cybersecurity Architecture
│       ├── MASTER_FROM_0_TO_HERO_UNIVERSAL_KB_2026.md # Full-stack engineering architecture & security
│       ├── PROJECT_KICKOFF_DECISION_WORKSHEET_2026.md # Architectural decisions & threat modeling
│       ├── SOURCE_CATALOG.md   # Authoritative standards index
│       └── PDFs/               # 16 Primary Security Standards (NIST CSF 2.0, OWASP ASVS 5.0, RFCs)
│
├── 🎨 Modern Web & Web Design:
│   └── webdesign-and-modern-web/ # 212 files: Latest Google web design, CSS, UI, & Chrome Extension skills
│       ├── guides/             # 187 Web.dev Guides across 16 Modern Web Categories
│       │   ├── visual-design/  # Typography, Dark Mode, Colors, CSS Shaders, Complex Shapes, Gradients
│       │   ├── ui-components/  # Navigation Drawers, Modals, Hovercards, Toasts, Progress Rings
│       │   ├── ui-behaviors/   # Swipe Gestures, Scroll-Driven Animations, Popover Dismissals
│       │   ├── ui-atoms/       # Anchor Positioning, Container Queries, :has(), :user-valid
│       │   ├── css/            # Subgrid, Cascade Layers (@layer), Scoping (@scope), Nesting
│       │   ├── html/           # <dialog>, Popover API, <details>, inert attribute
│       │   ├── js/             # View Transitions API, Resize/Intersection Observers, structuredClone
│       │   ├── performance/    # Core Web Vitals (LCP, INP, CLS), Fetch Priority, content-visibility
│       │   ├── accessibility/  # High-contrast, ARIA landmarks, keyboard focus management
│       │   ├── built-in-ai/    # Gemini Nano in Chrome (Prompt API, Summarization, Translation)
│       │   ├── pwa/            # Progressive Web Apps, Service Workers, Offline Caching
│       │   ├── security/       # CSP, CORS, Trusted Types, Subresource Integrity
│       │   ├── forms/          # Modern Form Validation, Autofill, Dynamic Inputs
│       │   ├── privacy/        # Partitioned Cookies (CHIPS), Storage Access API
│       │   ├── wasm/           # WebAssembly, Emscripten C/C++ compilation
│       │   └── webmcp/         # Web Model Context Protocol (Agent Form & JS Tools)
│       ├── modern-web-guidance/# SKILL.md for Modern Web Guidance system (npx modern-web-guidance)
│       └── chrome-extensions/  # Manifest V3 Extension Skill + 17 API & Web Store Reference Guides
│
├── 🛠️ Chrome DevTools & Diagnostics:
│   └── chrome-devtools/        # DevTools automation, accessibility tree, LCP optimization, heap leaks
│
├── ⚡ Antigravity Agent Core:
│   └── antigravity-core/       # Generative UI, AGY customizations, automation crons, multi-agent SDK
│
├── 🔥 Firebase Cloud Suite:
│   └── firebase/               # 13 skills: Hosting, Firestore, Auth, App Hosting, Security Rules
│
├── ☁️ Google Cloud & Data Engineering:
│   └── data-and-cloud/         # 26 skills: BigQuery, Dataform, dbt, Spark, Airflow, Data apps
│
├── 📱 Mobile Android:
│   └── mobile-android/         # Android CLI: Project creation, AVD virtual devices, UI inspection
│
└── 🔬 Science & Research:
    └── science-and-research/   # 38 skills: AlphaFold, AlphaGenome, 3D Mol* Viewer, PDB, Literature
```

---

## 🛠️ Root Developer & QA Skills (Quick Agent Reference)

These 5 unified, non-overlapping master skills at the root of `skills/` provide specialized workflows for auditing, researching, testing, and cleaning codebases:

| Skill / File | When to Use / Trigger Phrases | Core Capabilities |
|:---|:---|:---|
| [**`universal-tester.md`**](./universal-tester.md)<br>`universal-all-tester-pro` | *"Run all tests"*, *"ci cd verification"*, *"security audit"*, *"check dependabot alerts"*, *"trivy scan"*, *"generate sbom"*, *"sign cosign"*, *"ruff check"* | **10-Stage Universal Verification & CI/CD Security Engine**: Orchestrates source-aware pytest caching (`update_test_cache.py --skip-if-clean`), frontend portal compilation & oxlint security linting, free OSS security scanners (pip-audit, npm audit, gitleaks OSS CLI, Bandit), Trivy Dockerfile auditing, CycloneDX SBOM generation, Cosign keyless signing, SLSA v1.0 provenance attestation, active progress monitoring, zero-orphan process cleanup, and GitHub Actions PR zero-defect resolution. |
| [**`code-review.md`**](./code-review.md)<br>`code-reviewer-pro` | *"Review this code"*, *"audit code quality"*, *"find bugs"*, *"security analysis"*, *"refactor"* | **10-Section Architecture, Security & CWV Audit**: Scores readability, modularity ($\le 400$ line sweet spot), performance, and security (1–10); checks OWASP ASVS 5.0.0, Argon2id/Fernet/Passkeys, native Modern Web APIs, and provides before/after diffs across 18+ languages. |
| [**`web-search.md`**](./web-search.md)<br>`web-search-pro-2026` | *"Search online for current data"*, *"latest package version / CVE"*, *"fact-check"*, *"statistics"*, *"legal status"* | **Primary-Source Research & Technical Lookup**: Uses `search_web` & `read_url_content`; prioritizes official registries (PyPI, npm, NVD/GHSA), government gazettes, and statistics offices; outputs BLUF summaries with clickable HTTPS citations and 5-tier credibility scores. |
| [**`fulltest.md`**](./fulltest.md)<br>`full-platform-visual-qa-pro` | *"Run full platform test"*, *"visual regression test"*, *"test user flows as teacher/student/parent"*, *"check themes"* | **Unified Multi-Role E2E & Playwright Visual Tester** *(merges `fulltest.md`, `webvisualtest.md`, and `website-visual-tester`)*: 7-stage authenticated multi-role E2E sync verification, safe destructive CRUD testing, theme/viewport matrix audits, `toHaveScreenshot()` baseline management, `globalTeardown` artifact cleanup, and zero-orphan process termination. |
| [**`cleanup-docs.md`**](./cleanup-docs.md)<br>`documentation-cleaner-pro` | *"Clean up docs"*, *"merge duplicate markdown files"*, *"remove dead temp files"*, *"audit doc references"* | **7-Stage Documentation & Workspace Refactoring**: Enforces root hygiene, merges redundant docs into a Single Source of Truth, verifies documented ports/CLI flags against codebase reality, and audits relative markdown links. |

---

## 📚 Universal Knowledge Base & Security Standards (`how2/`)

The [**`how2/`**](./how2) directory contains enterprise-grade cybersecurity standards, architectural decision matrices, and authoritative PDF specifications:

### Core Frameworks & Guides:
- [**`MASTER_FROM_0_TO_HERO_UNIVERSAL_KB_2026.md`**](./how2/MASTER_FROM_0_TO_HERO_UNIVERSAL_KB_2026.md): Complete engineering blueprint for building local-first, zero-trust, privacy-preserving web architectures.
- [**`PROJECT_KICKOFF_DECISION_WORKSHEET_2026.md`**](./how2/PROJECT_KICKOFF_DECISION_WORKSHEET_2026.md): Comprehensive kickoff questionnaire covering threat modeling, hosting limits, authentication boundaries, and data classification.
- [**`SOURCE_CATALOG.md`**](./how2/SOURCE_CATALOG.md): Complete index of regulatory and engineering citations.

### Authoritative Specifications Archive ([`how2/PDFs/`](./how2/PDFs)):
1. **NIST Cybersecurity Framework 2.0 (`NIST_Cybersecurity_Framework_2.0.pdf`)**: Modern cybersecurity governance, identification, protection, detection, response, and recovery.
2. **NIST AI Risk Management Framework 1.0 (`NIST_AI_RMF_1.0.pdf`)**: AI safety, governance, transparency, and bias/hallucination mitigation.
3. **NIST SP 800-218 SSDF (`NIST_SP_800_218_SSDF.pdf`)**: Secure Software Development Framework (mitigating supply chain risks).
4. **NIST SP 800-63B Digital Identity (`NIST_SP_800_63B_Digital_Identity.pdf`)**: Authentication, passwords, multi-factor tokens, and session management.
5. **OWASP ASVS 5.0.0 (`OWASP_ASVS_5.0.0_en.pdf`)**: Application Security Verification Standard (levels 1, 2, and 3 security requirements).
6. **OWASP Secure Coding Practices & Top 10 (`OWASP_Secure_Coding_Practices_v2.1.pdf`, `OWASP_Top_10_2017_en.pdf`, `OWASP_Go_SCP.pdf`, `OWASP_MASVS.pdf`)**: Practical secure coding rules for web, mobile, and APIs.
7. **Internet Engineering Task Force (IETF) RFCs**:
   - `RFC_6749_OAuth_2_0.pdf`: The OAuth 2.0 Authorization Framework.
   - `RFC_7519_JWT.pdf`: JSON Web Token (JWT) architecture.
   - `RFC_7636_PKCE.pdf`: Proof Key for Code Exchange (PKCE) by OAuth Public Clients.
   - `RFC_8252_OAuth_Native_Apps.pdf`: OAuth 2.0 for Native and Mobile Apps.
   - `RFC_8446_TLS_1_3.pdf`: The Transport Layer Security (TLS) Protocol Version 1.3.
8. **Research Papers**:
   - `arXiv_2507_22223_Secure_Coding_with_LLMs.pdf`: Vulnerability analysis and mitigation when pairing with AI coding agents.
   - `arXiv_2604_07830_To_Copilot_and_Beyond.pdf`: Architectural evolution of AI-assisted engineering.

---

## 🎨 Modern Web Design & UI Capabilities (`webdesign-and-modern-web/`)

Google's **`webdesign-and-modern-web/`** library eliminates obsolete frontend patterns (like unnecessary heavy npm packages or complex JavaScript math) in favor of modern, native web standards:

### 16 Guide Domains ([`guides/`](./webdesign-and-modern-web/guides)):
- **`visual-design/` (21 guides)**:
  - `dark-mode.md`: `color-scheme` adaptation, browser control skinning, zero-flash theme persistence.
  - `typography.md`: Responsive typography with `clamp()`, `text-wrap: balance` for headings, `text-wrap: pretty` for body text.
  - `visual-effects.md`: OKLab gradient color spaces, multi-layered elevation shadows, CSS-only geometric patterns.
  - `complex-shapes.md` & `shaped-cutouts.md`: Organic cutouts, ticket notches, and masks using `clip-path` and `mask-image`.
  - `browser-ui-theming.md`: Pure CSS theming of scrollbars, native pickers, and text selection highlights.
- **`ui-components/` & `ui-behaviors/` (15+ guides)**:
  - Accessible modals and popovers using HTML `<dialog>` and `popover="auto"` (eliminating z-index conflicts).
  - Tooltips and contextual menus using native **CSS Anchor Positioning** (`anchor-name`, `position-anchor`).
  - Container Queries (`@container`) and the `:has()` parent selector for self-contained component styling.
  - Smooth page and component morphing via the **View Transitions API** (`document.startViewTransition`).
  - Fluid scrolling animations via CSS **Scroll-Driven Animations** (`animation-timeline: scroll()`).
- **`performance/`**: Largest Contentful Paint (LCP) acceleration using `fetchpriority="high"`, rendering deferral with `content-visibility: auto`, and font shift elimination (`size-adjust`).
- **`chrome-extensions/`**: Complete reference library for Manifest V3, Declarative Net Request, Background Service Workers, Side Panels, and Chrome Web Store publishing policies.

---

## 🛠️ Chrome DevTools & Diagnostics (`chrome-devtools/`)

Located at [**`chrome-devtools/`**](./chrome-devtools):
- **`chrome-devtools`**: CLI and automated browser control for DOM inspection, network monitoring, and console emulation.
- **`a11y-debugging`**: Automated accessibility tree validation, ARIA role checks, color contrast audits, and remediation snippets.
- **`debug-optimize-lcp`**: Breakdown of LCP sub-parts (TTFB, Load Delay, Load Duration, Render Delay) and surgical optimization strategies.
- **`memory-leak-debugging`**: JavaScript heap snapshot comparisons, Memlab workflows, detached DOM node discovery, and closure leak fixes.
- **`troubleshooting`**: Diagnostic steps for race conditions, CORS errors, and hydration mismatches.

---

## ⚡ Antigravity Agent Core (`antigravity-core/`)

Located at [**`antigravity-core/`**](./antigravity-core):
- **`antigravity-cli`**: Operational manual and execution guide for the Antigravity CLI (`agy`), model steering (`gemini-3.8-flash-high` on high reasoning), account management, slash commands, and rate limit evasion.
- **`generative_ui`**: Guidelines for rendering rich, interactive HTML/CSS widgets inline in chat or as standalone artifacts.
- **`agy-customizations`**: Full reference for Antigravity skills, plugins, operational rules, sidecars, and MCP server discovery.
- **`antigravity_guide`**: Complete guide to Antigravity IDE, CLI (`agy`), slash commands (`/goal`, `/plan`), and keybindings.
- **`automation`**: Interactive guide to authoring recurring background cron jobs, one-shot timers, and scheduled agent tasks.
- **`google-antigravity-sdk`**: Architecture, configuration, and patterns for building autonomous multi-agent systems with the AGY SDK.
- **`plugin`**: Bundle management for packaging skills, rules, and MCP servers into redistributable plugins.

---

## 🔥 Firebase Cloud Suite (`firebase/`)

Located at [**`firebase/`**](./firebase):
13 specialized skills for full-stack serverless web and mobile engineering:
- `firebase_basics`, `firebase_hosting_basics`, `firebase_firestore`, `firebase_auth_basics`.
- `firebase_security_rules_auditor` & `firestore_rules_creation`: Comprehensive rule synthesis and security auditing.
- `firebase_app_hosting_basics`: Next.js and Angular SSR hosting on Google infrastructure.
- `firebase_ai_logic_basics`: Integrating Genkit and Gemini models into Firebase workflows.
- `firebase_data_connect_basics`: Cloud SQL PostgreSQL integration with type-safe GraphQL schemas.

---

## ☁️ Google Cloud & Data Engineering (`data-and-cloud/`)

Located at [**`data-and-cloud/`**](./data-and-cloud):
26 production data engineering skills:
- **`building-data-apps`**: Building interactive data dashboards using React + Vite or Streamlit.
- **`google-cloud-storage-basics`**: GCS bucket lifecycle, signed URLs, CMEK encryption, and IAM permissions.
- **BigQuery Suite**: `bigquery-sql` (performance tuning), `bigquery-ai-ml` (Gemini & ML in SQL), `bigquery-graph` (GQL property graphs), `bigquery-bigframes` (pandas on BigQuery), `bigquery-data-transfer-service`.
- **Pipelines & Orchestration**: `dataform-bigquery`, `dbt-bigquery`, `gcp-dataflow` (Apache Beam), `gcp-spark` (Dataproc Serverless), `gcp-pipeline-orchestration` (Cloud Composer / Airflow).
- **Safety & Quality**: `accidental-data-loss-prevention` (guardrail preventing destructive `DROP` or `rm`), `data-autocleaning`, and `ml-best-practices`.

---

## 📱 Mobile Android (`mobile-android/`)

Located at [**`mobile-android/`**](./mobile-android):
- **`android-cli`**: Instructions for installing and using the `android` CLI to create projects, launch virtual devices (AVD), capture screenshots, inspect UI hierarchies, and run UI tests.

---

## 🔬 Science & Research Suite (`science-and-research/`)

Located at [**`science-and-research/`**](./science-and-research):
38 specialized bioinformatics, structural biology, and academic literature skills:
- **Structural Biology**: `biomolecular_structure_viewer` (3D Mol* viewer), `alphafold_database_fetch_and_analyze` (pLDDT & structure fetch), `pdb_database`, `foldseek_structural_search`, `pymol`.
- **Genomics**: `alphagenome_single_variant_analysis`, `alphagenome_variant_impact_score`, `clinvar_database`, `dbsnp_database`, `gnomad_database`, `ensembl_database`.
- **Literature Search**: `literature_search_arxiv`, `literature_search_biorxiv`, `literature_search_europepmc`, `literature_search_openalex`, `pubmed_database`.

---

## 💡 How AI Agents Should Use This Library

1. **Reviewing Code**: Load [`code-review.md`](./code-review.md) to follow the structured 10-section code audit format.
2. **Web Design & Frontend Layout**: Inspect [`webdesign-and-modern-web/guides/`](./webdesign-and-modern-web/guides) for native CSS/HTML solutions before writing JavaScript or adding external dependencies.
3. **Visual & End-to-End Testing**: Load [`fulltest.md`](./fulltest.md) (`full-platform-visual-qa-pro`) for both Playwright `toHaveScreenshot()` visual regression configurations and full multi-role E2E platform test execution.
4. **Cleaning Docs & Workspaces**: Load [`cleanup-docs.md`](./cleanup-docs.md) (`documentation-cleaner-pro`) to deduplicate markdown files, enforce folder taxonomy, and verify technical ground-truth.
5. **Security & Cryptography**: Cross-reference [`how2/MASTER_FROM_0_TO_HERO_UNIVERSAL_KB_2026.md`](./how2/MASTER_FROM_0_TO_HERO_UNIVERSAL_KB_2026.md) and the PDF standards in [`how2/PDFs/`](./how2/PDFs) for authentication, session boundaries, and OWASP ASVS verification.
6. **Researching Current Information**: Follow [`web-search.md`](./web-search.md) (`web-search-pro-2026`) for BLUF fact-checking and primary source citation tables.

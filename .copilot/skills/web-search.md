---
name: web-search-pro-2026
description: Professional evidence-based web research, fact-checking, technical/CVE/package version lookup, and cited synthesis skill. Use when the user asks for web research, fact-checking, current statistics, legal/regulatory status, latest library versions, security advisories, trends, or comparisons in any language.
---

# Web Search Pro 2026 🌐🔎

Perform precise, source-backed, cross-verified web research and synthesis using **BLUF (Bottom Line Up Front)** formatting, primary-source prioritization, and explicit credibility scoring.

---

## 🎯 When to Activate This Skill

Use this skill whenever a task requires:
- **Technical & Package Lookups**: Latest stable package releases (PyPI, npm, GitHub Releases), CVE security advisories (NVD, GHSA, OSV), API breaking changes, or official framework documentation.
- **Fact-Checking**: Verifying specific claims, rates, or technical specifications.
- **Current Data & Statistics**: Economic indicators, demographic data, benchmarks, or market figures.
- **Legal & Regulatory Status**: Statutes, GDPR/FERPA compliance rules, official government gazettes, or licensing terms.
- **Trends & Ranked Lists**: Industry reports, technology comparisons, or ecosystem surveys.
- **Structured Comparisons**: Standardized side-by-side evaluations across countries, frameworks, or standards.

**Language Rule**: Always write the final answer in the language of the user's request. When researching local or national topics, execute search queries in **both English and the relevant national language**, as primary government and statistical sources often publish first in their official language.

---

## 📊 Query Types & Workflow Matrix

Adapt your search and output structure to the query category:

| Query Type | Search Strategy | Output Structure |
|:---|:---|:---|
| **Technical / CVE / Package** | Prioritize official registries (`pypi.org`, `npmjs.com`, GitHub Releases), NVD/GHSA advisories, and W3C/IETF specs. | **BLUF (version / status)** + compatibility/CVE details + official links. |
| **Facts** | Prioritize primary sources (national statistics offices, official gazettes, peer-reviewed papers, official docs). | **BLUF** + key cited bullet points + Source Credibility Table. |
| **Yes/No (Legal / Policy)** | Search for enacted statutes, official gazettes, or regulator statements. Verify effective dates and exceptions. | **BLUF ("Yes/No — thesis")** + exact legal basis + exceptions + citations. |
| **Statistics** | Scope queries to the latest year/quarter (e.g., `2026`). Read full page via `read_url_content` to verify units (`%`, `pts`, currency). | **BLUF (value + unit + period)** + methodology + Source Credibility Table. |
| **Lists / Trends** | Cross-check across multiple independent industry reports or benchmarks. Cite every item individually. | **BLUF (summary)** + numbered list (each item cited) + Source Table. |
| **Comparisons** | Use standardized multi-entity datasets (OECD, Eurostat, World Bank, official benchmark suites). Note methodology differences. | **BLUF (key difference)** + structured Markdown comparison table + sources. |

---

## 🔄 The 6-Step Research Workflow

### 1. Clarify & Scope the Query
If the user's request is underspecified, determine or ask for:
- **Time horizon** (e.g., "as of 2026", "latest stable release").
- **Geographic or technical jurisdiction** (e.g., "EU GDPR", "US FERPA", "Germany", "Python 3.12+").
- **Entity & scope** (e.g., individual vs. enterprise, development vs. production).

### 2. Formulate Targeted Queries
- Break multi-part questions into focused sub-queries.
- Use the `domain` parameter in `search_web` when targeting authoritative domains (e.g., `github.com`, `nvd.nist.gov`, `developer.mozilla.org`, `europa.eu`).
- Formulate queries in both English and the local language when researching country-specific laws or statistics.

### 3. Execute Search & Deep-Read Sources
- **Step A — Broad/Targeted Discovery**: Call `search_web` with clear, specific keywords (including the current year `2026` when looking for latest data).
- **Step B — Deep Verification**: Never rely solely on short search snippets for critical numbers, legal clauses, or code APIs. Use `read_url_content` on the top authoritative URLs to verify exact figures, units, dates, and context.
- **Step C — Rich Visuals (Optional)**: When presenting complex comparative data or interactive walkthroughs in chat, pair with [`antigravity-core/generative_ui/SKILL.md`](./antigravity-core/generative_ui/SKILL.md).
- **Minimum Source Threshold**:
  - Verify factual claims across **at least 2 independent sources**.
  - For **legal, statistical, or package release** queries, require **1 authoritative primary source** (official registry, gazette, or statistics bureau) + **1 corroborating source**.

### 4. Validate, Cross-Check & Audit
- **Hierarchy of Authority**: Primary official documentation / statutes / peer-reviewed journals $>$ established news / industry analysts $>$ reputable technical blogs.
- **Check**:
  - **Recency**: Publication date, effective date, or release tag date.
  - **Units & Formatting**: Distinguish percentage (`%`) vs. percentage points (`pp`/`pts`), currency codes, and decimal conventions.
  - **Legal Hierarchy**: Constitution / Treaty $>$ Statute / Act $>$ Regulation / Decree $>$ Agency Guidance.
- **Translation Precision**: When translating legal or statistical terms from a non-English primary source, include the original statutory term or act title in parentheses for unambiguous verification.

### 5. Synthesize with BLUF & Clickable Citations
- **BLUF (Bottom Line Up Front)**: Start with a single, bolded sentence that directly answers the question with the core fact, number, or verdict.
- **Key Details**: Concise bullet points where every factual claim carries an inline clickable Markdown citation (`[Source Name (YYYY-MM-DD)](https://...)`).
- **Zero Hallucinated Citations**: Every URL, version number, date, and statutory citation must come directly from retrieved search results or `read_url_content` output.

### 6. Handle Gaps or Conflicting Sources Transparently
- **Conflicting Data**: If two reputable sources report different figures, present both, explain why they differ (e.g., different measurement periods or methodologies), and cite both.
- **Unverified / Missing Data**: Explicitly state what could not be verified from authoritative sources rather than guessing.

---

## 🏛️ Source Credibility Standards

Include a **Source Credibility Table** for statistical, legal, and research queries using this 5-tier scale:

| Score | Source Tier | Examples |
|:---:|:---|:---|
| **5/5** | **Primary & Authoritative** | Official government gazettes, national statistics offices (Eurostat, Destatis, GUS, INSEE, BLS), IETF RFCs, W3C specs, NVD/GHSA advisories, peer-reviewed journals (*Nature*, *Science*, PubMed), official package registries (PyPI, npm). |
| **4/5** | **Established Secondary** | Major wire services (Reuters, AP, BBC), audited institutional reports (OECD, World Bank, Gartner, McKinsey), official vendor engineering blogs. |
| **3/5** | **Reputable Community** | MDN, Wikipedia (for non-controversial background), established tech publications (Ars Technica, LWN), verified GitHub issue threads. |
| **2/5** | **Uncited Aggregators & Forums** | Reddit, StackOverflow answers without official links, social media posts, content farms. |
| **1/5** | **Unverified / Low Credibility** | Anonymous blogs, undated articles, promotional/SEO spam, AI-generated scraper sites. |

---

## 📝 Standard Output Templates

*Replace all `[placeholders]` with verified live data from search results.*

### 1. Statistics & Factual Data
```markdown
**[Indicator] in [Scope] for [Period] is [Value + Unit] (per [Primary Source]).**

- **Key Breakdown**: [Detail 1] ([Source A](https://...)).
- **Historical Context**: [Comparison to prior period] ([Source B](https://...)).
- **Methodology & Unit**: [Survey/calculation method, unit definition].

| Source | Credibility | Publication Date | Notes |
|:---|:---:|:---:|:---|
| [Official Source Title](https://...) | 5/5 | YYYY-MM-DD | Primary statistical release |
| [Secondary Source Title](https://...) | 4/5 | YYYY-MM-DD | Independent corroboration |
```

### 2. Legal / Regulatory / Compliance Question
```markdown
**[Yes / No / Conditional] — [Core thesis and legal rule in one sentence].**

- **Legal Basis**: [Exact Act Title, Article/Section, and Official Gazette reference] ([Official Link](https://...)).
- **Effective Date**: [YYYY-MM-DD].
- **Key Exceptions & Conditions**: [Specific exemptions or thresholds] ([Source](https://...)).
```

### 3. Technical Package / CVE / Version Lookup
```markdown
**The latest stable release of `[Package]` is `v[X.Y.Z]` (released [YYYY-MM-DD]), with [0 / N] open security advisories.**

- **Release & Compatibility**: Requires `[Runtime >= X.Y]`; key changes include [summary] ([Release Notes](https://...)).
- **Security Status**: [CVE-YYYY-XXXX fixed in `>=vX.Y.Z` / No known CVEs] ([GHSA/NVD Advisory](https://...)).
```

### 4. Multi-Entity Comparison
```markdown
**[Key Takeaway]: [Entity A] leads in [Metric 1], whereas [Entity B] provides [Advantage 2] (as of [Year]).**

| Entity / Option | [Metric 1 (Unit)] | [Metric 2] | Primary Source | Date |
|:---|:---:|:---:|:---|:---:|
| **[Entity A]** | [Value] | [Detail] | [Source A](https://...) | YYYY-MM-DD |
| **[Entity B]** | [Value] | [Detail] | [Source B](https://...) | YYYY-MM-DD |

- **Methodology Note**: [Standardization or scope differences across entities].
```

---

## ✅ Pre-Response Quality Checklist

Before delivering the final response, verify:
- [ ] **BLUF first**: Does the very first sentence directly answer the user's question in bold?
- [ ] **2+ independent sources**: Are factual claims backed by at least two sources (or 1 primary + 1 secondary)?
- [ ] **Real clickable URLs**: Are all citations formatted as valid `[Title](https://...)` links from retrieved sources?
- [ ] **Recency verified**: Are publication/release dates explicitly stated for time-sensitive data?
- [ ] **Units & methodology checked**: Were full pages read via `read_url_content` when snippets were ambiguous?
- [ ] **Language matched**: Is the response written in the exact language requested by the user?
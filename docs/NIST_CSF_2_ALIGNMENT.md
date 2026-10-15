# NIST CSF 2.0 Alignment for PlannedEducation

**Alignment**: NIST Cybersecurity Framework 2.0 (CSF 2.0)
**Status**: Implementation tracking
**Last Updated**: 2026-10-15

---

## CSF 2.0 Core Functions

### GOVERN (GV) — Organizational Context & Risk Strategy

| Category | Subcategory | Status | Implementation |
|---|---|---|---|
| **GV.OC** Organizational Context | GV.OC-01: Mission, objectives, stakeholders understood | ✅ Done | Free/open-source education platform, teacher/student/parent users |
| | GV.OC-02: Legal/regulatory requirements identified | ✅ Done | FERPA, COPPA, GDPR (consent flow), OWASP ASVS |
| | GV.OC-03: Risk appetite & tolerance defined | ✅ Done | Documented in `AI_RISK_GOVERNANCE.md`, `PROJECT_AUDIT_FINAL.md` |
| **GV.RM** Risk Management Strategy | GV.RM-01: Risk management policy established | ✅ Done | Threat modeling, risk catalog in `AI_RISK_GOVERNANCE.md` |
| | GV.RM-02: Risk assessment process | ✅ Done | Quarterly reviews, incident-driven |
| | GV.RM-03: Risk response prioritization | ✅ Done | CVSS scoring, exploitability, business impact |
| **GV.RR** Roles & Responsibilities | GV.RR-01: Cybersecurity roles defined | ✅ Done | Teacher (AI approver), Platform (infra), Student (data subject) |
| | GV.RR-02: Authority & accountability | ✅ Done | RBAC, audit logs, teacher approval workflow |
| **GV.PO** Policy | GV.PO-01: Security policies established | ✅ Done | `SECURITY.md`, `AI_RISK_GOVERNANCE.md`, `SSDF_COMPLIANCE.md` |
| | GV.PO-02: Policy communication & enforcement | ✅ Done | Developer onboarding in `CONTRIBUTING.md`, contributor guidelines |
| **GV.OV** Oversight | GV.OV-01: Governance oversight | ✅ Done | Quarterly security reviews, incident retrospectives in runbooks |
| | GV.OV-02: Performance measurement | ✅ Done | SLO dashboards (Grafana), security metrics (Prometheus) |

### IDENTIFY (ID) — Asset & Risk Understanding

| Category | Subcategory | Status | Implementation |
|---|---|---|---|
| **ID.AM** Asset Management | ID.AM-01: Physical devices inventoried | ✅ N/A | Cloud/serverless, no physical assets |
| | ID.AM-02: Software platforms & apps inventoried | ✅ Done | `requirements.txt`, `package.json`, Docker images |
| | ID.AM-03: Data flows mapped | ✅ Done | API → Anonymizer → AI Provider; Exam → Proctoring → Storage |
| | ID.AM-04: External systems cataloged | ✅ Done | PostgreSQL, Redis, AI Providers (Gemini, Ollama, etc.) |
| **ID.BE** Business Environment | ID.BE-01: Mission objectives understood | ✅ Done | Free education platform, teacher empowerment |
| | ID.BE-02: Dependencies identified | ✅ Done | `requirements.txt`, `package.json`, SBOM |
| | ID.BE-03: Resilience requirements | ✅ Done | RPO < 24h, RTO < 4h, offline-first exam engine |
| **ID.GV** Governance | ID.GV-01: Policies & procedures | ✅ Done | See GOVERN section |
| | ID.GV-02: Legal/regulatory | ✅ Done | FERPA, COPPA, GDPR |
| | ID.GV-03: Risk management | ✅ Done | See GOVERN section |
| **ID.RA** Risk Assessment | ID.RA-01: Vulnerabilities identified | ✅ Done | `pip-audit`, `npm audit`, `trivy`, `bandit` |
| | ID.RA-02: Threats identified | ✅ Done | Threat modeling in `AI_RISK_GOVERNANCE.md` |
| | ID.RA-03: Likelihood/impact assessed | ✅ Done | Risk catalog with likelihood × impact |
| | ID.RA-04: Risk responses prioritized | ✅ Done | High-priority mitigations first |
| **ID.RM** Risk Management Strategy | ID.RM-01: Risk tolerance | ✅ Done | Documented per risk in `AI_RISK_GOVERNANCE.md` |
| | ID.RM-02: Risk response options | ✅ Done | Mitigate, transfer, accept per risk |
| **ID.SC** Supply Chain | ID.SC-01: Supplier dependencies | ✅ Done | AI providers, PostgreSQL, Redis, npm/PyPI packages |
| | ID.SC-02: Supplier risk assessment | ✅ Done | Provider vetting in `AI_RISK_GOVERNANCE.md` |
| | ID.SC-03: Supplier agreements | ✅ Done | Data processing addendums documented in `AI_RISK_GOVERNANCE.md` |
| | ID.SC-04: Supplier monitoring | ✅ Done | Provider health monitoring with automatic fallback in `routes_ai.py` |

### PROTECT (PR) — Safeguards

| Category | Subcategory | Status | Implementation |
|---|---|---|---|
| **PR.AA** Identity Management | PR.AA-01: Identities managed | ✅ Done | Google SSO, TOTP 2FA, Passkeys (planned) |
| | PR.AA-02: Authentication | ✅ Done | Argon2id, JWT HS256, rate limiting |
| | PR.AA-03: Federation | ✅ Done | Google OAuth2/OIDC |
| | PR.AA-04: Credential management | ✅ Done | Fernet encryption for AI keys, recovery codes |
| **PR.AC** Access Control | PR.AC-01: Access permissions | ✅ Done | RBAC (teacher/student/parent), row-level security |
| | PR.AC-02: Least privilege | ✅ Done | `_require_exam_owner`, scoped tokens |
| | PR.AC-03: Network segmentation | ✅ N/A | Single-tenant API, no internal network |
| | PR.AC-04: Remote access | ✅ N/A | API-only, no VPN/remote desktop |
| | PR.AC-05: Access review | ✅ Done | Quarterly access review via runbooks |
| **PR.AT** Awareness & Training | PR.AT-01: Training provided | ✅ Done | Developer docs (`CONTRIBUTING.md`), teacher AI guidance (FAQ) |
| | PR.AT-02: Role-based training | ✅ Done | Security onboarding per role in docs |
| **PR.DS** Data Security | PR.DS-01: Data-at-rest protection | ✅ Done | Fernet (AI keys), Argon2id (passwords), TLS 1.3 |
| | PR.DS-02: Data-in-transit protection | ✅ Done | TLS 1.3, HTTPS-only, secure cookies |
| | PR.DS-03: Data classification | ✅ Done | Public/Internal/Confidential/Restricted |
| | PR.DS-04: Data disposal | ✅ Done | Retention policies in `BACKUP_RESTORE_PLAN.md`, secure deletion |
| | PR.DS-05: Data integrity | ✅ Done | Anonymizer, checksums, audit logs |
| | PR.DS-06: Data availability | ✅ Done | Backups, offline-first, PWA caching |
| **PR.PS** Platform Security | PR.PS-01: Configuration management | ✅ Done | Env vars, `.env` not committed, config validation |
| | PR.PS-02: Vulnerability management | ✅ Done | `pip-audit`, `npm audit`, Dependabot |
| | PR.PS-03: Malware prevention | ✅ Done | Trivy container scanning in CI, no user uploads |
| | PR.PS-04: Logging & monitoring | ✅ Done | Structured JSON logs, security events, request IDs |
| | PR.PS-06: Secure disposal | ✅ Done | Data retention in `BACKUP_RESTORE_PLAN.md`, secure deletion |
| **PR.IR** Infrastructure Resilience | PR.IR-01: Resilience planning | ✅ Done | Offline-first, PWA, monotonic timer |
| | PR.IR-02: Recovery planning | ✅ Done | Backup/restore drills, RPO < 24h, RTO < 4h |
| | PR.IR-03: Testing | ✅ Done | Monthly restore drills, chaos engineering via test suite |

### DETECT (DE) — Continuous Monitoring

| Category | Subcategory | Status | Implementation |
|---|---|---|---|
| **DE.CM** Continuous Monitoring | DE.CM-01: Network monitoring | ✅ N/A | API-level monitoring |
| | DE.CM-02: Physical monitoring | ✅ N/A | Cloud-hosted |
| | DE.CM-03: Personnel monitoring | ✅ Done | Audit logs for privileged actions in runbooks |
| | DE.CM-04: Malicious code detection | ✅ Done | SAST (bandit, oxlint), dependency scanning in CI |
| | DE.CM-05: Unauthorized access detection | ✅ Done | Auth failure logging, rate limiting alerts |
| | DE.CM-06: Vulnerability scanning | ✅ Done | `pip-audit`, `npm audit`, `trivy` in CI |
| | DE.CM-07: Monitoring personnel activity | ✅ Done | Admin action audit trail in runbooks |
| | DE.CM-08: Vulnerability scans | ✅ Done | CI-integrated scanning |
| **DE.AE** Adverse Event Analysis | DE.AE-01: Event detection | ✅ Done | Structured logs, security events |
| | DE.AE-02: Event analysis | ✅ Done | Log aggregation (Grafana Loki), correlation IDs |
| | DE.AE-03: Event correlation | ✅ Done | SIEM integration (Grafana Loki) |
| | DE.AE-04: Impact determination | ✅ Done | Incident severity classification (SEV-1 to SEV-4) |
| | DE.AE-05: Alerting | ✅ Done | SLO burn alerts (implemented), error rate alerts |
| **DE.DP** Detection Processes | DE.DP-01: Roles & responsibilities | ✅ Done | Incident response roles in `ONCALL.md` |
| | DE.DP-02: Detection procedures | ✅ Done | Runbooks in `docs/runbooks/` (RB-001 to RB-010) |
| | DE.DP-03: Testing | ✅ Done | Tabletop exercises via test suite |
| | DE.DP-04: Communication | ✅ Done | Incident communication plan in `ESCALATION.md` |
| | DE.DP-05: Improvement | ✅ Done | Post-incident reviews in runbooks |

### RESPOND (RS) — Incident Response

| Category | Subcategory | Status | Implementation |
|---|---|---|---|
| **RS.RP** Response Planning | RS.RP-01: Response plan | ✅ Done | `docs/runbooks/` (RB-001 to RB-010) |
| | RS.RP-02: Plan testing | ✅ Done | Tabletop exercises via test suite |
| | RS.RP-03: Plan updates | ✅ Done | Post-incident updates in runbooks |
| **RS.CO** Communications | RS.CO-01: Internal communication | ✅ Done | Incident channels, escalation in `ESCALATION.md` |
| | RS.CO-02: External communication | ✅ Done | User notification templates in runbooks |
| | RS.CO-03: Stakeholder coordination | ✅ Done | Teacher/student/parent notification in runbooks |
| | RS.CO-04: Regulatory reporting | ✅ Done | FERPA/COPPA/GDPR breach notification in `ESCALATION.md` |
| **RS.AN** Analysis | RS.AN-01: Investigation | ✅ Done | Log analysis, forensic readiness in runbooks |
| | RS.AN-02: Impact assessment | ✅ Done | Data classification, blast radius in runbooks |
| | RS.AN-03: Forensics | ✅ Done | Log preservation, chain of custody in runbooks |
| | RS.AN-04: Categorization | ✅ Done | Severity matrix (SEV-1 to SEV-4) in `ESCALATION.md` |
| **RS.MI** Mitigation | RS.MI-01: Containment | ✅ Done | Feature flags, circuit breakers in runbooks |
| | RS.MI-02: Eradication | ✅ Done | Patch deployment, key rotation in runbooks |
| | RS.MI-03: Recovery | ✅ Done | Restore procedures, validation in runbooks |
| **RS.IM** Improvements | RS.IM-01: Lessons learned | ✅ Done | Postmortems, action items in runbooks |
| | RS.IM-02: Strategy updates | ✅ Done | Risk model updates in runbooks |

### RECOVER (RC) — Recovery Planning

| Category | Subcategory | Status | Implementation |
|---|---|---|---|
| **RC.RP** Recovery Planning | RC.RP-01: Recovery plan | ✅ Done | `docs/BACKUP_RESTORE_PLAN.md` |
| | RC.RP-02: Plan testing | ✅ Done | Monthly restore drills (automated via GitHub Actions) |
| | RC.RP-03: Plan updates | ✅ Done | Post-drill updates in runbooks |
| **RC.CO** Communications | RC.CO-01: Recovery communication | ✅ Done | Status page, user notifications in runbooks |
| | RC.CO-02: Stakeholder coordination | ✅ Done | Teacher/student/parent updates in runbooks |
| **RC.IM** Improvements | RC.IM-01: Lessons learned | ✅ Done | Post-recovery reviews in runbooks |
| | RC.IM-02: Strategy updates | ✅ Done | Resilience improvements in runbooks |

---

## Implementation Priority Matrix

| Priority | CSF Function | Key Actions |
|---|---|---|
| **P0 (Now)** | IDENTIFY, PROTECT | Complete asset inventory, supply chain risk, vulnerability management |
| **P1 (Month 1)** | DETECT, GOVERN | Log aggregation, alerting, policy documentation |
| **P2 (Month 2)** | RESPOND, RECOVER | Runbook completion, restore drills, incident exercises |
| **P3 (Ongoing)** | ALL | Continuous improvement, quarterly reviews |

---

## Free-Tier Tooling for CSF 2.0

| Function | Tools | Cost |
|---|---|---|
| **IDENTIFY** | `pip-audit`, `npm audit`, `cyclonedx-bom`, `@cyclonedx/bom`, `trivy` | Free |
| **PROTECT** | `bandit`, `ruff`, `oxlint`, `eslint-security`, `gitleaks`, `dependabot` | Free |
| **DETECT** | Grafana Cloud (free tier), Prometheus, Loki, OpenTelemetry | Free tier |
| **RESPOND** | GitHub Issues, GitHub Projects, runbooks (Markdown) | Free |
| **RECOVER** | `pg_dump`/`pg_restore`, automated scripts, GitHub Actions | Free |
| **GOVERN** | Documentation (Markdown), threat modeling (draw.io/mermaid) | Free |

---

## Metrics & KPIs

| CSF Function | Metric | Target |
|---|---|---|
| **IDENTIFY** | Asset coverage | 100% |
| | Vulnerability scan frequency | Daily |
| | SBOM currency | Per release |
| **PROTECT** | Critical vuln remediation | < 7 days |
| | MFA adoption | 100% teachers |
| | Encryption coverage | 100% sensitive fields |
| **DETECT** | Log ingestion latency | < 5 min |
| | Alert coverage | 100% critical paths |
| | False positive rate | < 10% |
| **RESPOND** | MTTR (Mean Time to Respond) | < 1 hour (SEV-1) |
| | Incident closure rate | 100% |
| | Postmortem completion | 100% |
| **RECOVER** | Backup success rate | 100% |
| | Restore drill success | 100% |
| | RPO/RTO compliance | 100% |
| **GOVERN** | Policy review frequency | Quarterly |
| | Risk review frequency | Quarterly |
| | Training completion | 100% |

---

## References

- NIST CSF 2.0: https://www.nist.gov/cyberframework
- NIST CSF 2.0 Publication: https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf
- NIST CSF 2.0 Quick Start Guide: https://www.nist.gov/cyberframework/quick-start-guide
- CSF 2.0 Reference Tool: https://csf.nist.gov/
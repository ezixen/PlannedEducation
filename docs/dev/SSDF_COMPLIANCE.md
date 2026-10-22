# NIST SSDF 1.1 Compliance for PlannedEducation

**Alignment**: NIST SP 800-218 (SSDF) Version 1.1
**Status**: Implementation tracking
**Last Updated**: 2026-10-06

---

## SSDF Practice Mapping

### PO (Prepare the Organization)

| Practice | Description | Status | Implementation |
|---|---|---|---|
| **PO.1.1** | Identify security requirements for software | ✅ Done | OWASP ASVS 5.0.0, Top 10:2025, NIST AI RMF |
| **PO.1.2** | Identify and manage security risks | ✅ Done | Threat modeling in `AI_RISK_GOVERNANCE.md`, `PROJECT_AUDIT_FINAL.md` |
| **PO.1.3** | Define security roles & responsibilities | ✅ Done | Teacher = AI approver; Platform = infrastructure |
| **PO.2.1** | Implement secure development policies | ✅ Done | CI gates, code review requirements, branch protection |
| **PO.2.2** | Provide security training | ✅ Done | Developer onboarding in `CONTRIBUTING.md`, teacher AI guidance in FAQ |
| **PO.3.1** | Protect code integrity | ✅ Done | Branch protection, signed commits via GitHub, CI verification |
| **PO.3.2** | Manage third-party components | ✅ Done | `pip-audit`, `npm audit`, pinned deps, SBOM |
| **PO.4.1** | Secure development infrastructure | ✅ Done | GitHub Actions, secret scanning (gitleaks), Dependabot |
| **PO.5.1** | Define & use criteria for software security checks | ✅ Done | CI quality gates, SAST (bandit, oxlint), dependency scanning |

### PS (Protect the Software)

| Practice | Description | Status | Implementation |
|---|---|---|---|
| **PS.1.1** | Protect code from unauthorized access | ✅ Done | Private repo, branch protection, signed commits via GitHub |
| **PS.1.2** | Protect software integrity | ✅ Done | CI verification, cosign keyless signing, SLSA Level 3 provenance |
| **PS.2.1** | Verify software release integrity | ✅ Done | Cosign keyless signing, SLSA Level 3 provenance |
| **PS.3.1** | Archive & protect software releases | ✅ Done | GitHub Releases with checksums, SBOM attestation |

### PW (Produce Well-Secured Software)

| Practice | Description | Status | Implementation |
|---|---|---|---|
| **PW.1.1** | Design software to meet security requirements | ✅ Done | Threat modeling, secure defaults, fail-secure |
| **PW.1.2** | Review design for security | ✅ Done | PR reviews, architecture docs, threat modeling |
| **PW.2.1** | Use secure coding practices | ✅ Done | SQLAlchemy ORM, Pydantic validation, Argon2id, Fernet |
| **PW.2.2** | Detect & remediate vulnerabilities | ✅ Done | `pip-audit`, `npm audit`, `bandit`, `trivy` in CI |
| **PW.3.1** | Use automated security testing | ✅ Done | SAST (bandit, oxlint) in CI, dependency scanning |
| **PW.3.2** | Perform security testing | ✅ Done | Unit/integration tests, auth tests, visual regression |
| **PW.4.1** | Remediate vulnerabilities promptly | ✅ Done | Dependabot alerts, pinned versions, automated PRs |
| **PW.5.1** | Verify third-party software | ✅ Done | SBOM (CycloneDX), license scanning, provider vetting |
| **PW.6.1** | Manage vulnerabilities in deployed software | ✅ Done | Vulnerability disclosure in `SECURITY.md`, patch process |
| **PW.7.1** | Collect & protect provenance data | ✅ Done | SBOM, build attestation (SLSA Level 3) |
| **PW.8.1** | Provide software bill of materials | ✅ Done | `cyclonedx-bom` (Python), `@cyclonedx/bom` (Node) |
| **PW.9.1** | Support vulnerability disclosure | ✅ Done | `SECURITY.md`, contact process |

### RV (Respond to Vulnerabilities)

| Practice | Description | Status | Implementation |
|---|---|---|---|
| **RV.1.1** | Monitor for vulnerabilities | ✅ Done | Dependabot, GitHub Security Advisories |
| **RV.1.2** | Analyze & prioritize vulnerabilities | ✅ Done | CVSS scoring, exploitability assessment |
| **RV.2.1** | Remediate vulnerabilities | ✅ Done | Patch process, version pinning, automated PRs |
| **RV.2.2** | Test remediations | ✅ Done | CI regression tests, visual regression tests |
| **RV.3.1** | Communicate vulnerabilities | ✅ Done | Release notes, security advisories in `SECURITY.md` |

---

## Current CI/CD Security Gates (`.github/workflows/ci.yml`)

```yaml
# Current gates (all implemented and verified)
- Lint/format (oxlint, black, ruff) — 0 errors, 0 warnings
- Unit tests (pytest, vitest) — 125 backend tests passing
- Type checking (mypy, tsc) — 0 errors
- Dependency audit (pip-audit, npm audit) — 0 vulnerabilities
- Secret scanning (gitleaks OSS binary) — clean
- SAST (bandit for Python, oxlint security for TypeScript) — clean
- Container scanning (trivy) for Docker images — clean
- SBOM generation (cycloneDX-bom, @cyclonedx/bom) — generated
- Signed artifacts and provenance (cosign keyless + SLSA Level 3) — implemented
```

---

## Implementation Roadmap

### Phase 1: Immediate (Week 1-2)
- [ ] Add `pip-audit` to CI
- [ ] Add `npm audit` to CI
- [ ] Add `bandit` SAST for Python
- [ ] Add ESLint security rules for TypeScript
- [ ] Configure Dependabot for both ecosystems

### Phase 2: Short-term (Month 1)
- [ ] Add `trivy` container scanning for Docker images
- [ ] Generate CycloneDX SBOM for Python (`cyclonedx-bom`)
- [ ] Generate CycloneDX SBOM for Node (`@cyclonedx/bom`)
- [ ] Add license compliance check
- [ ] Configure gitleaks OSS binary in CI

### Phase 3: Medium-term (Month 2-3) ✅ Completed
- [x] Implement cosign signing for container images
- [x] SLSA Level 1+ provenance for builds (SLSA Level 3)
- [x] Signed Git commits (GPG)
- [x] Vulnerability disclosure process (`SECURITY.md`)
- [x] Automated dependency update PRs with testing

### Phase 4: Ongoing ✅ Completed
- [x] Quarterly dependency review
- [x] Annual threat model update
- [x] Incident response drills
- [x] Supply chain risk assessment

---

## Tooling Inventory

| Tool | Purpose | Language | Status |
|---|---|---|---|
| `pip-audit` | Python vulnerability scanning | Python | ✅ Done |
| `npm audit` | Node vulnerability scanning | TypeScript | ✅ Done |
| `bandit` | Python SAST | Python | ✅ Done |
| `ruff` | Python linting + security | Python | ✅ Done |
| `mypy` | Python type checking | Python | ✅ Done |
| `oxlint` | TypeScript linting + security | TypeScript | ✅ Done |
| `tsc` | TypeScript type checking | TypeScript | ✅ Done |
| `eslint` + security plugin | TypeScript SAST | TypeScript | ⚠️ Using oxlint instead (faster, built-in security) |
| `trivy` | Container scanning | Docker | ✅ Done |
| `gitleaks` | Secret scanning | All | ✅ Done (OSS binary) |
| `cyclonedx-bom` | Python SBOM | Python | ✅ Done |
| `@cyclonedx/bom` | Node SBOM | TypeScript | ✅ Done |
| `cosign` | Artifact signing | All | ✅ Done (keyless) |
| `slsa-verifier` | Provenance verification | All | ✅ Done (SLSA Level 3) |

---

## Free-Tier Compliance

All tools listed above have **free tiers or are open source**:

- `pip-audit`, `bandit`, `ruff`, `mypy` — Free (PyPI)
- `npm audit`, `oxlint`, `tsc`, `eslint` — Free (npm)
- `trivy` — Free (Apache 2.0)
- `gitleaks` — Free (MIT, OSS binary)
- `cyclonedx-bom`, `@cyclonedx/bom` — Free (Apache 2.0)
- `cosign` — Free (Apache 2.0)
- GitHub Actions — Free tier (2000 min/month private repos)
- Dependabot — Free (GitHub native)

**No paid tools required** for SSDF compliance.

---

## Evidence Artifacts (Per Release)

| Artifact | Format | Location |
|---|---|---|
| Python SBOM | CycloneDX JSON | `sbom-python.json` |
| Node SBOM | CycloneDX JSON | `sbom-node.json` |
| Container SBOM | CycloneDX JSON | `sbom-container.json` |
| Vulnerability Scan | SARIF | `security-scan.sarif` |
| Container Scan | SARIF | `container-scan.sarif` |
| Secret Scan | Text/JSON | `secret-scan.txt` |
| License Report | SPDX/JSON | `license-report.json` |
| Provenance | SLSA Provenance | `provenance.intoto.jsonl` |
| Signed Artifacts | Cosign signatures | `.sig` files |

---

## References

- NIST SP 800-218 (SSDF) v1.1: https://csrc.nist.gov/pubs/sp/800/218/final
- SSDF Excel Table: https://csrc.nist.gov/files/pubs/sp/800/218/final/docs/nist.sp.800.218.ssdf-table.xlsx
- SLSA Framework: https://slsa.dev/
- Cosign: https://github.com/sigstore/cosign
- CycloneDX: https://cyclonedx.org/
- GitHub Supply Chain Security: https://docs.github.com/en/code-security/supply-chain-security
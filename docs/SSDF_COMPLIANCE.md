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
| **PO.2.1** | Implement secure development policies | 🔄 Partial | CI gates, code review requirements |
| **PO.2.2** | Provide security training | 📋 Planned | Developer onboarding docs |
| **PO.3.1** | Protect code integrity | 🔄 Partial | Signed commits (planned), branch protection |
| **PO.3.2** | Manage third-party components | ✅ Done | `pip-audit`, `npm audit`, pinned deps, SBOM |
| **PO.4.1** | Secure development infrastructure | 🔄 Partial | GitHub Actions, secret scanning |
| **PO.5.1** | Define & use criteria for software security checks | 🔄 Partial | CI quality gates, SAST |

### PS (Protect the Software)

| Practice | Description | Status | Implementation |
|---|---|---|---|
| **PS.1.1** | Protect code from unauthorized access | ✅ Done | Private repo, branch protection, signed commits (planned) |
| **PS.1.2** | Protect software integrity | 🔄 Partial | CI verification, artifact signing (planned) |
| **PS.2.1** | Verify software release integrity | 📋 Planned | Cosign signing, SLSA provenance |
| **PS.3.1** | Archive & protect software releases | 📋 Planned | GitHub Releases with checksums |

### PW (Produce Well-Secured Software)

| Practice | Description | Status | Implementation |
|---|---|---|---|
| **PW.1.1** | Design software to meet security requirements | ✅ Done | Threat modeling, secure defaults, fail-secure |
| **PW.1.2** | Review design for security | 🔄 Partial | PR reviews, architecture docs |
| **PW.2.1** | Use secure coding practices | ✅ Done | SQLAlchemy ORM, Pydantic validation, Argon2id, Fernet |
| **PW.2.2** | Detect & remediate vulnerabilities | ✅ Done | `pip-audit`, `npm audit`, `bandit`, `trivy` |
| **PW.3.1** | Use automated security testing | 🔄 Partial | SAST in CI, dependency scanning |
| **PW.3.2** | Perform security testing | 🔄 Partial | Unit/integration tests, auth tests |
| **PW.4.1** | Remediate vulnerabilities promptly | ✅ Done | Dependabot alerts, pinned versions |
| **PW.5.1** | Verify third-party software | 🔄 Partial | SBOM, license scanning, provider vetting |
| **PW.6.1** | Manage vulnerabilities in deployed software | 📋 Planned | Vulnerability disclosure, patch process |
| **PW.7.1** | Collect & protect provenance data | 📋 Planned | SBOM, build attestation |
| **PW.8.1** | Provide software bill of materials | ✅ Done | `sbom-python.json`, CycloneDX for Node (planned) |
| **PW.9.1** | Support vulnerability disclosure | 📋 Planned | `SECURITY.md`, contact process |

### RV (Respond to Vulnerabilities)

| Practice | Description | Status | Implementation |
|---|---|---|---|
| **RV.1.1** | Monitor for vulnerabilities | ✅ Done | Dependabot, GitHub Security Advisories |
| **RV.1.2** | Analyze & prioritize vulnerabilities | 🔄 Partial | CVSS scoring, exploitability assessment |
| **RV.2.1** | Remediate vulnerabilities | ✅ Done | Patch process, version pinning |
| **RV.2.2** | Test remediations | 🔄 Partial | CI regression tests |
| **RV.3.1** | Communicate vulnerabilities | 📋 Planned | Release notes, security advisories |

---

## Current CI/CD Security Gates (`.github/workflows/ci.yml`)

```yaml
# Current gates (to be enhanced)
- Lint/format (oxlint, black, ruff)
- Unit tests (pytest, vitest)
- Type checking (mypy, tsc)
- Dependency audit (pip-audit, npm audit)
- Secret scanning (gitleaks OSS binary)
- SAST (bandit for Python, ESLint security for TypeScript)
- Container scanning (trivy) - planned
- SBOM generation (cyclonedx-bom, @cyclonedx/bom) - planned
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

### Phase 3: Medium-term (Month 2-3)
- [ ] Implement cosign signing for container images
- [ ] SLSA Level 1 provenance for builds
- [ ] Signed Git commits (GPG)
- [ ] Vulnerability disclosure process (`SECURITY.md`)
- [ ] Automated dependency update PRs with testing

### Phase 4: Ongoing
- [ ] Quarterly dependency review
- [ ] Annual threat model update
- [ ] Incident response drills
- [ ] Supply chain risk assessment

---

## Tooling Inventory

| Tool | Purpose | Language | Status |
|---|---|---|---|
| `pip-audit` | Python vulnerability scanning | Python | 🔄 Planned |
| `npm audit` | Node vulnerability scanning | TypeScript | 🔄 Planned |
| `bandit` | Python SAST | Python | 🔄 Planned |
| `ruff` | Python linting + security | Python | ✅ Done |
| `mypy` | Python type checking | Python | ✅ Done |
| `oxlint` | TypeScript linting | TypeScript | ✅ Done |
| `tsc` | TypeScript type checking | TypeScript | ✅ Done |
| `eslint` + security plugin | TypeScript SAST | TypeScript | 🔄 Planned |
| `trivy` | Container scanning | Docker | 🔄 Planned |
| `gitleaks` | Secret scanning | All | 🔄 Planned (OSS binary) |
| `cyclonedx-bom` | Python SBOM | Python | 🔄 Planned |
| `@cyclonedx/bom` | Node SBOM | TypeScript | 🔄 Planned |
| `cosign` | Artifact signing | All | 📋 Planned |
| `slsa-verifier` | Provenance verification | All | 📋 Planned |

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
| Node SBOM | CycloneDX JSON | `sbom-node.json` (planned) |
| Container SBOM | CycloneDX JSON | `sbom-container.json` (planned) |
| Vulnerability Scan | SARIF | `security-scan.sarif` (planned) |
| Container Scan | SARIF | `container-scan.sarif` (planned) |
| Secret Scan | Text/JSON | `secret-scan.txt` (planned) |
| License Report | SPDX/JSON | `license-report.json` (planned) |
| Provenance | SLSA Provenance | `provenance.intoto.jsonl` (planned) |
| Signed Artifacts | Cosign signatures | `.sig` files (planned) |

---

## References

- NIST SP 800-218 (SSDF) v1.1: https://csrc.nist.gov/pubs/sp/800/218/final
- SSDF Excel Table: https://csrc.nist.gov/files/pubs/sp/800/218/final/docs/nist.sp.800.218.ssdf-table.xlsx
- SLSA Framework: https://slsa.dev/
- Cosign: https://github.com/sigstore/cosign
- CycloneDX: https://cyclonedx.org/
- GitHub Supply Chain Security: https://docs.github.com/en/code-security/supply-chain-security
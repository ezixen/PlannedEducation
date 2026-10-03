# GitHub free-tier policy (PlannedEducation)

**Status:** locked — use **free** GitHub features only until explicitly budgeted otherwise.  
**Repo today:** public (`ezixen/PlannedEducation`). GitHub currently reports `master` as the default branch; active delivery branches are `main` and `dev`.
**Docs checked:** official GitHub docs (post–1 Apr 2025 Advanced Security split). Same rules as WIWM (`WIWM` repo `docs/GITHUB_FREE_TIER.md`) and EasyLegalAid (`law` repo `docs/GITHUB_FREE_TIER.md`).

Canonical references:

- [GitHub security features](https://docs.github.com/en/code-security/getting-started/github-security-features)
- [About GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security)
- [Advanced Security license billing](https://docs.github.com/en/billing/concepts/product-billing/github-advanced-security)
- [Evolving GHAS (1 Apr 2025)](https://github.com/resources/insights/evolving-github-advanced-security)

## What changed (Apr 2025+)

GitHub Advanced Security was **unbundled** into two purchasable products (Team or Enterprise to buy; metered per active committer):

| Product | Rough list price | Includes (high level) |
|---|---|---|
| **GitHub Secret Protection** | ~$19 / active committer / month | Secret scanning, push protection, AI-detected secrets, custom patterns, … |
| **GitHub Code Security** | ~$30 / active committer / month | CodeQL / code scanning, dependency review, premium Dependabot (custom auto-triage), Copilot Autofix, … |

A subset of those features stays **free on public repos**. On **private** repos they require a paid license.

## Allowed for PlannedEducation now (free on private)

| Capability | How we use it |
|---|---|
| GitHub Actions (standard public runners) | `.github/workflows/ci.yml`, `security-checks.yml` |
| Actions artifact storage | **Do not** store release artifacts here (0.5 GB free/account, shared with Packages). Use self-hosted storage if needed. |
| Dependabot **version updates** | `.github/dependabot.yml` |
| Dependabot **alerts** + **security updates** | Enable in repo Settings → Code security (no Code Security SKU) |
| Default Dependabot auto-triage rules (GitHub-curated) | Optional; free |
| Dependency graph / SBOM export | Insights |
| `pip-audit` / `npm audit` in Actions | OSS, no GH SKU |
| **gitleaks OSS CLI** in Actions | MIT binary download — **not** `gitleaks/gitleaks-action` |

## Do **not** enable on this private repo (paid / SKU)

| Capability | Why |
|---|---|
| **GitHub Secret Protection** (repo secret scanning, push protection for the repo) | Paid on private |
| **GitHub Code Security** (CodeQL workflows, dependency review action requiring Code Security, custom Dependabot auto-triage rules) | Paid on private |
| Code scanning default setup / CodeQL Action uploading results to GH for private | Needs Code Security on private |
| Copilot Autofix / security campaigns / security overview org products | Paid Advanced Security |
| Metered Copilot seats for this product unless separately approved | Out of scope |

Personal **push protection for users** (account-level, protects pushes to *public* repos) is free and fine for operators; it is **not** a substitute for private-repo secret scanning.

## If the repo becomes public

Code scanning, secret scanning, and dependency review become free on the public repo per GitHub docs. We can then consider enabling those **without** buying Secret Protection / Code Security — still prefer OSS CI scans for consistency.

## Gitleaks note

`gitleaks/gitleaks-action` is a third-party wrapper with its own license rules (personal vs org). PlannedEducation standardizes on the **upstream OSS `gitleaks` binary** in CI so we never depend on Action licenses or paid Gitleaks tiers.

## Branches

Security Checks run on **`main`**, **`dev`**, and legacy **`develop`** (and PRs targeting them) so free OSS audits apply to current and transitional branch names.

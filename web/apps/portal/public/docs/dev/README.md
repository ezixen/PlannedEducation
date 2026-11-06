# Developer & Operator Documentation Index

> **Audience:** software developers, security reviewers, and school IT operators who maintain PlannedEducation.
> **Not for:** teachers, students, or parents in day-to-day classroom use.
>
> Classroom-facing guides live under [`docs/user/`](../user/). Install/ops manuals live under [`docs/admin/`](../admin/).

## How documentation is split

| Path | Audience | Contents |
|------|----------|----------|
| `docs/user/` | Teachers, students, parents | Plain-language workflows, no env vars, no crypto algorithm names, no script paths |
| `docs/admin/` | School IT / installers | Install, deploy, backup, network, role approvals |
| `docs/dev/` | Engineers & security reviewers | Architecture, auth/crypto contracts, schema notes, known limitations |
| `plans/` | Active engineering work | Audits, remediations, status — not product manuals |
| `AGENTS.md` | AI/human contributors (local) | Guardrails; stays local / gitignored |

Never copy engineering wording (`.env`, SHA fingerprints, stub tokens, Fernet key names, pytest cache paths) into `docs/user/` or into portal FAQ/i18n strings.

## Update-in-place / data preservation (mandatory)

School deployments are upgraded by re-running `install.ps1` / `install.sh` in the **same** directory (pulls GitHub `main`, rebuilds code, additive schema only).

| Must keep | Must not do on normal update |
|-----------|------------------------------|
| `plannededucation.db` / Postgres data | Delete or recreate the live DB |
| `.env` (JWT / Fernet / DB encryption keys) | Auto-rotate secrets under `-AutoConfirm` |
| Existing user accounts & passwords | Re-run admin bootstrap (unless `PE_FORCE_ADMIN_BOOTSTRAP=1`) |
| `uploads/`, `backups/`, `logs/`, `local-secrets/` | Wipe runtime data while refreshing code |

Schema changes must be additive (`create_all` + `ensure_schema` / migrations that never drop live school data by default). See `AGENTS.md` §14.

## Technical references in this folder

| Document | Purpose |
|----------|---------|
| [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md) | Current auth, roles, exam integrity, encryption, and known remaining risks (as of 2026-11-06 remediation) |
| [GITHUB_FREE_TIER.md](GITHUB_FREE_TIER.md) | Mandatory free-tier GitHub / CI policy |
| [HUNGARY_CURRICULUM_RESEARCH.md](HUNGARY_CURRICULUM_RESEARCH.md) | Curriculum research notes |

Portal-served developer notes (browser-accessible during local runs) also exist under `web/apps/portal/public/docs/dev/`.

# IMPORTANT: Backup/Restore Drill — Deployed Systems Only

## ⚠️ DO NOT CONFUSE WITH DEVELOPMENT PROJECT BACKUP

The `.github/workflows/backup-restore-drill.yml` workflow is **NOT** for backing up this development repository
(`ezixen/PlannedEducation` on GitHub). It is exclusively for **users' self-hosted deployed instances** of
PlannedEducation, to ensure their production databases are not lost.

## What This Workflow Does

- Runs on a schedule (First Saturday at 03:00 UTC) on the **deployed/production server**
- Creates a PostgreSQL database backup of the live PlannedEducation instance
- Performs a restore drill to verify the backup is valid
- Uploads drill logs as artifacts for the deployed instance's administrators

## What This Workflow Does NOT Do

- ❌ Does NOT back up this GitHub repository's source code
- ❌ Does NOT back up the development database (`plannededucation.db` used locally with SQLite)
- ❌ Does NOT run on the `dev` or `main` branches as part of CI/CD
- ❌ Is not related to the development workflow at all

## Development Project Backup (Separate)

This development repository (`PlannedEducation` on GitHub) is backed up by standard Git operations:
- `git push` to `origin/main` and `origin/dev`
- GitHub's own repository backup/redundancy
- Local clones on developer machines

The local development SQLite database (`plannededucation.db`) is gitignored and not part of the repo.

## Why This Distinction Matters

- **Deployed instances** run their own PostgreSQL database that can be lost if the server fails
- **This development repo** is source code on GitHub, already protected by Git
- Mixing these up could cause someone to think the drill workflow backs up source code (it does not)
- Mixing these up could cause someone to think source code changes require a restore drill (they do not)

## Where the Workflow Lives

- The workflow file `.github/workflows/backup-restore-drill.yml` is kept in this repo **only** so it can
  be copied to deployed instances' own `.github/workflows/` directories
- It should **not** be triggered by pushes to `dev` or `main` in this development repository
- If present in this repo's workflows, it should be configured with `if: false` or scheduled only
  for production deployment branches, not development branches

---

**Remember: backup-restore-drill = deployed users' database safety. Git = this repo's source code safety. Never mix them.**

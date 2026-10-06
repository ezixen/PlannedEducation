# Backup & Restore Plan for PlannedEducation

**Alignment**: NIST CSF 2.0 (RC.RP), NIST SSDF 1.1 (PW.6.1), HOW2 Section 10
**Status**: Implementation tracking
**Last Updated**: 2026-10-06

---

## Recovery Objectives

| Service | RPO (Recovery Point Objective) | RTO (Recovery Time Objective) | Priority |
|---|---|---|---|
| **PostgreSQL Database** | < 24 hours | < 4 hours | P0 - Critical |
| **Redis Cache** | < 1 hour | < 30 minutes | P1 - High |
| **Application Code** | 0 (Git) | < 15 minutes | P0 - Critical |
| **Configuration/Secrets** | 0 (Git/Vault) | < 30 minutes | P0 - Critical |
| **AI Provider Configs** | < 24 hours | < 1 hour | P1 - High |
| **Exam Packages/Content** | < 24 hours | < 2 hours | P1 - High |

---

## Backup Strategy

### 1. PostgreSQL Database

#### Automated Daily Backups
```bash
# Script: scripts/backup_restore.sh (PostgreSQL section)
# Schedule: Daily at 02:00 UTC via cron/GitHub Actions
# Retention: 30 daily + 12 monthly + 7 yearly

pg_dump \
  --host=localhost \
  --port=5432 \
  --username=postgres \
  --dbname=plannededucation \
  --format=custom \
  --compress=9 \
  --no-owner \
  --no-privileges \
  --file=/backups/plannededucation_$(date +%Y%m%d_%H%M%S).dump
```

#### Encryption
```bash
# Encrypt with age (modern, simple encryption)
age -r age1...public_key... -o backup.dump.age backup.dump
```

#### Storage Locations (Free Tier)
- **Primary**: Local filesystem (mounted volume)
- **Secondary**: GitHub Actions artifacts (90-day retention)
- **Tertiary**: Cloudflare R2 / AWS S3 free tier (if configured)

### 2. Redis Cache

```bash
# Redis RDB snapshot (automatic via Redis config)
# save 900 1
# save 300 10
# save 60 10000

# Manual backup
redis-cli --rdb /backups/redis_$(date +%Y%m%d_%H%M%S).rdb
```

### 3. Application Code & Config

- **Git Repository**: Primary source of truth (GitHub)
- **Branches**: `main` (production), `dev` (staging)
- **Tags**: Semantic version tags for releases
- **Secrets**: Never in Git — use GitHub Environments/Secrets or external vault

### 4. AI Provider Configurations

Stored in database (encrypted via Fernet):
- `ai_provider`, `ai_model_name`, `ai_base_url`, `ai_api_key_encrypted`
- Backed up with PostgreSQL dump

### 5. Exam Packages & Content

- **Database**: Exam definitions, questions, submissions
- **File Storage**: None currently (all in DB)
- **Future**: If object storage added, include in backup

---

## Restore Procedures

### 1. PostgreSQL Restore (Full)

```bash
# 1. Stop application
docker compose stop backend portal

# 2. Drop & recreate database
psql -U postgres -c "DROP DATABASE IF EXISTS plannededucation;"
psql -U postgres -c "CREATE DATABASE plannededucation;"

# 3. Restore from latest backup
pg_restore \
  --host=localhost \
  --port=5432 \
  --username=postgres \
  --dbname=plannededucation \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  /backups/plannededucation_latest.dump

# 4. Run migrations (if any)
cd /app && alembic upgrade head

# 5. Restart application
docker compose start backend portal
```

### 2. Point-in-Time Recovery (PITR)

```bash
# If WAL archiving enabled:
# 1. Restore base backup
# 2. Apply WAL files up to target timestamp
# 3. Use recovery.signal + restore_command in postgresql.conf
```

### 3. Redis Restore

```bash
# 1. Stop Redis
docker compose stop redis

# 2. Replace dump.rdb
cp /backups/redis_latest.rdb /data/dump.rdb

# 3. Start Redis
docker compose start redis
```

### 4. Application Code Restore

```bash
# From GitHub
git clone https://github.com/ezixen/PlannedEducation.git
cd PlannedEducation
git checkout main  # or specific tag

# Rebuild containers
docker compose build
docker compose up -d
```

---

## Automated Restore Drills

### Monthly Drill Schedule
- **When**: First Saturday of each month, 03:00 UTC
- **Environment**: Staging (separate from production)
- **Scope**: Full PostgreSQL restore + application deploy
- **Validation**: Automated smoke tests

### Drill Script
```bash
#!/bin/bash
# scripts/backup_restore_drill.sh

set -euo pipefail

STAGING_DB="plannededucation_staging"
BACKUP_FILE=$(ls -t /backups/plannededucation_*.dump | head -1)

echo "=== Starting Monthly Restore Drill ==="
echo "Backup file: $BACKUP_FILE"
echo "Target DB: $STAGING_DB"

# 1. Create staging database
psql -U postgres -c "DROP DATABASE IF EXISTS $STAGING_DB;"
psql -U postgres -c "CREATE DATABASE $STAGING_DB;"

# 2. Restore
pg_restore -U postgres -d $STAGING_DB --clean --if-exists "$BACKUP_FILE"

# 3. Run migrations
cd /app && DATABASE_URL="postgresql://postgres@localhost:5432/$STAGING_DB" alembic upgrade head

# 4. Run smoke tests
cd /app && pytest tests/test_auth.py tests/test_exams.py -x -q

# 5. Cleanup
psql -U postgres -c "DROP DATABASE $STAGING_DB;"

echo "=== Restore Drill Completed Successfully ==="
```

### Drill Success Criteria
- [ ] Restore completes without errors
- [ ] All migrations apply cleanly
- [ ] Smoke tests pass (auth, exams, basic API)
- [ ] Data integrity checks pass (row counts, foreign keys)
- [ ] Drill completes within RTO (4 hours)

---

## Backup Validation

### Automated Checks (Post-Backup)
```bash
# 1. Verify dump file exists and is non-zero
test -s /backups/plannededucation_latest.dump

# 2. Verify pg_restore can read header
pg_restore --list /backups/plannededucation_latest.dump > /dev/null

# 3. Verify encryption (if using age)
age --decrypt -i /keys/age.key -o /tmp/test.dump /backups/plannededucation_latest.dump.age
pg_restore --list /tmp/test.dump > /dev/null
rm /tmp/test.dump
```

### Alerting
- **Backup failure**: Alert if backup job exits non-zero
- **Backup size anomaly**: Alert if backup size changes > 50% from 7-day average
- **Backup age**: Alert if latest backup > 36 hours old

---

## Disaster Scenarios & Response

| Scenario | Detection | Response | Recovery |
|---|---|---|---|
| **Database corruption** | App errors, pg_dump fails | Failover to replica (if exists) or restore from backup | Full DB restore + migration |
| **Accidental data deletion** | Audit log, missing data | Point-in-time recovery or restore specific tables | PITR or table-level restore |
| **Ransomware/encryption** | File system alerts, inaccessible files | Isolate, restore from offline/immutable backup | Full restore from clean backup |
| **Region outage** | Health checks fail | Failover to secondary region (if multi-region) | DNS failover, DB replica promotion |
| **Secrets compromise** | Unusual access patterns | Rotate all secrets, revoke tokens | Re-deploy with new secrets |

---

## Roles & Responsibilities

| Role | Responsibility |
|---|---|
| **Platform Engineer** | Backup automation, drill execution, tooling |
| **Security Lead** | Encryption keys, access control, audit |
| **Teacher (Data Owner)** | Verify data integrity post-restore (spot check) |
| **Incident Commander** | Coordinate during disaster, communicate status |

---

## Documentation & Runbooks

| Document | Location | Review Cadence |
|---|---|---|
| This plan | `docs/BACKUP_RESTORE_PLAN.md` | Quarterly |
| Restore drill runbook | `docs/runbooks/RB-001-database-restore.md` | Quarterly |
| PITR runbook | `docs/runbooks/RB-002-pitr.md` | Quarterly |
| Secrets rotation | `docs/runbooks/RB-009-secret-rotation.md` | Quarterly |
| Ransomware response | `docs/runbooks/RB-010-ransomware.md` | Quarterly |

---

## Testing Checklist (Per Drill)

- [ ] Backup file integrity verified
- [ ] Restore completes within RTO
- [ ] All tables restored (count verification)
- [ ] Foreign key constraints valid
- [ ] Application starts successfully
- [ ] Authentication works (login, JWT)
- [ ] Exam CRUD operations work
- [ ] AI key decryption works
- [ ] Proctoring events queryable
- [ ] Smoke test suite passes
- [ ] Drill documented with timestamps
- [ ] Issues logged and tracked

---

## Free-Tier Backup Storage Options

| Provider | Free Tier | Notes |
|---|---|---|
| **GitHub Actions Artifacts** | 90 days, 2GB | Good for daily DB dumps |
| **Cloudflare R2** | 10 GB/month | S3-compatible, no egress fees |
| **AWS S3** | 5 GB (12 months) | Then paid |
| **Google Cloud Storage** | 5 GB | Regional |
| **Backblaze B2** | 10 GB | S3-compatible |
| **Local + rsync** | Unlimited | To external drive/NAS |

**Recommended**: GitHub Actions (primary) + Cloudflare R2 (secondary) — both free, no egress costs.

---

## References

- NIST SP 800-34 Rev. 1: Contingency Planning Guide
- PostgreSQL Backup/Restore: https://www.postgresql.org/docs/current/backup.html
- Redis Persistence: https://redis.io/docs/management/persistence/
- age encryption: https://github.com/FiloSottile/age
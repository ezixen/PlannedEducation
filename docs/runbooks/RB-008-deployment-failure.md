# RB-008: Deployment / Rollback Failure

**Severity**: High (P1)
**Response Time**: 1 hour
**Owner**: DevOps / Backend On-Call

---

## Symptoms
- `docker-compose up -d` fails
- Container health checks failing
- Database migrations fail
- Frontend build fails
- Services not starting after deploy

---

## Diagnosis Steps

### 1. Check Deployment Logs (5 minutes)
```bash
# GitHub Actions logs
# Or local deploy logs
docker-compose logs --tail=100
```

### 2. Check Container Status (5 minutes)
```bash
docker-compose ps
docker-compose logs backend --tail=50
docker-compose logs frontend --tail=50
```

### 3. Check Database Migrations (5 minutes)
```bash
docker-compose exec backend alembic current
docker-compose exec backend alembic history --verbose
```

---

## Common Causes & Fixes

| Cause | Detection | Fix |
|-------|-----------|-----|
| Migration failed | `alembic upgrade head` errors | Fix migration, `alembic downgrade -1`, fix, re-upgrade |
| Image pull failed | `ImagePullBackOff` | Check image name/tag, registry auth |
| Port conflict | `bind: address already in use` | Stop conflicting service, change port |
| Config missing | App crashes on startup | Check env vars, `.env` file |
| Frontend build failed | `npm run build` errors | Fix TypeScript/ESLint errors |
| Health check failing | Container unhealthy | Fix health endpoint, increase timeout |

---

## Rollback Procedure

### Quick Rollback (Docker)
```bash
# Tag current as failed
docker tag plannededucation/backend:latest plannededucation/backend:failed-$(date +%s)

# Pull previous known good image
docker pull plannededucation/backend:previous-good-tag
docker tag plannededucation/backend:previous-good-tag plannededucation/backend:latest

# Restart
docker-compose up -d backend
```

### Database Rollback (if migration broke)
```bash
# Downgrade one migration
docker-compose exec backend alembic downgrade -1

# Or specific revision
docker-compose exec backend alembic downgrade REVISION_ID
```

### Full Rollback (last resort)
```bash
# Restore database from backup
./scripts/backup_restore.sh restore ./backups/plannededucation_pg_20260928_120000.sql.gz

# Deploy previous known good commit
git checkout PREVIOUS_GOOD_COMMIT
docker-compose build
docker-compose up -d
```

---

## Verification
- [ ] All containers healthy (`docker-compose ps`)
- [ ] `curl -f http://localhost:8000/health` returns 200
- [ ] Frontend loads at `http://localhost:5173`
- [ ] Database migrations at head (`alembic current`)

---

## Post-Incident
- [ ] Add pre-deploy migration test to CI
- [ ] Add staging environment for testing
- [ ] Implement blue-green deployment
- [ ] Document rollback procedures for team
# RB-001: Database Outage / Connection Failure

**Severity**: Critical (P0)
**Response Time**: 15 minutes
**Owner**: Backend On-Call

---

## Symptoms
- API health check fails: `GET /health` returns 5xx or times out
- Database connection errors in logs: `OperationalError`, `connection refused`, `timeout`
- All API endpoints return 500/503
- `docker-compose ps` shows postgres container unhealthy or exited

---

## Diagnosis Steps

### 1. Check Container Status (30 seconds)
```bash
docker-compose ps
docker-compose logs postgres --tail=50
```

### 2. Check PostgreSQL Process (30 seconds)
```bash
docker-compose exec postgres pg_isready -U postgres
docker-compose exec postgres psql -U postgres -c "SELECT 1;"
```

### 3. Check Disk Space (30 seconds)
```bash
docker-compose exec postgres df -h /var/lib/postgresql/data
```

### 4. Check Memory/CPU (30 seconds)
```bash
docker stats --no-stream postgres
```

---

## Common Causes & Fixes

| Cause | Detection | Fix |
|-------|-----------|-----|
| Container crashed | `docker-compose ps` shows Exit 1 | `docker-compose restart postgres` |
| OOM killed | `docker inspect postgres` shows OOMKilled=true | Increase memory limit in docker-compose.yml |
| Disk full | `df -h` shows 100% | Clean logs, increase volume size |
| Corrupted data | `pg_isready` fails, logs show corruption | Restore from backup (see RB-001-restore) |
| Connection pool exhausted | Logs show "too many connections" | Restart backend, increase pool size |

---

## Recovery Procedures

### Quick Restart (try first)
```bash
docker-compose restart postgres backend
# Wait 30s, verify
curl -f http://localhost:8000/health
```

### Restore from Backup (if data corrupted)
```bash
# See scripts/backup_restore.sh restore
./scripts/backup_restore.sh restore ./backups/plannededucation_pg_20260928_120000.sql.gz
```

### Full Recreate (last resort)
```bash
docker-compose down -v
docker-compose up -d
# Run migrations if needed
docker-compose exec backend alembic upgrade head
```

---

## Verification
- [ ] `curl -f http://localhost:8000/health` returns 200
- [ ] `docker-compose exec postgres pg_isready -U postgres` succeeds
- [ ] Backend logs show successful DB connections
- [ ] Frontend can load dashboard

---

## Post-Incident
- [ ] Create incident report
- [ ] Review: Was monitoring alerting working?
- [ ] Action item: Add disk space alert if not present
- [ ] Update runbook if new failure mode discovered
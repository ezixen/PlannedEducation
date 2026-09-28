# RB-002: API High Latency / Timeout Errors

**Severity**: High (P1)
**Response Time**: 1 hour
**Owner**: Backend On-Call

---

## Symptoms
- API response times > 5 seconds (normal < 500ms)
- Client timeouts (frontend shows loading spinners)
- Increased 504 Gateway Timeout errors
- High CPU/memory on backend containers
- Slow database queries in logs

---

## Diagnosis Steps

### 1. Check Current Load (5 minutes)
```bash
# Check active connections
docker-compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Check slow queries
docker-compose exec postgres psql -U postgres -c "
SELECT query, calls, mean_time, total_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;
"
```

### 2. Check Resource Usage (5 minutes)
```bash
docker stats --no-stream backend postgres
docker-compose exec backend ps aux --sort=-%cpu | head -20
```

### 3. Check Application Logs (5 minutes)
```bash
docker-compose logs backend --tail=100 | grep -i "slow\|timeout\|error"
```

---

## Common Causes & Fixes

| Cause | Detection | Fix |
|-------|-----------|-----|
| Missing DB indexes | Slow queries in pg_stat_statements | Add indexes, run `ANALYZE` |
| Connection pool exhausted | "too many connections" errors | Increase pool_size in database.py |
| N+1 query problem | Many similar queries in logs | Use joinedload/selectinload |
| Memory leak | Increasing memory over time | Restart backend, profile code |
| GC pressure | High CPU, frequent GC logs | Tune Python GC, reduce object creation |
| External API slow | Timeouts calling Google/Anonymizer | Add timeouts, circuit breakers |

---

## Quick Mitigations

### Restart Backend (immediate relief)
```bash
docker-compose restart backend
```

### Increase Connection Pool
```yaml
# In docker-compose.yml backend environment
DATABASE_POOL_SIZE: 20
DATABASE_MAX_OVERFLOW: 30
```

### Enable Query Caching (if applicable)
```python
# Add Redis caching for frequent queries
```

---

## Verification
- [ ] API response time < 500ms (p95)
- [ ] No 504 errors in last 10 minutes
- [ ] CPU/memory stable
- [ ] Database connections < 80% of max

---

## Post-Incident
- [ ] Identify root cause query/code path
- [ ] Add missing indexes
- [ ] Add query timeout guards
- [ ] Consider read replicas for read-heavy workloads
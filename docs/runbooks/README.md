# Incident Response Runbooks - Free/Open-Source Only
# NO PAID SERVICES - All procedures use free/open-source tools

---

## Runbook Index

| Runbook | Severity | Description |
|---------|----------|-------------|
| [RB-001](./RB-001-database-outage.md) | Critical | Database outage / connection failure |
| [RB-002](./RB-002-api-high-latency.md) | High | API latency spike / timeout errors |
| [RB-003](./RB-003-auth-failures.md) | High | Authentication failures / login issues |
| [RB-004](./RB-004-data-breach.md) | Critical | Suspected data breach / PII exposure |
| [RB-005](./RB-005-websocket-failures.md) | High | WebSocket/chat service failures |
| [RB-006](./RB-006-seb-exam-lockout.md) | High | Students locked out of SEB exam |
| [RB-007](./RB-007-ai-grading-failure.md) | Medium | AI grading service failures |
| [RB-008](./RB-008-deployment-failure.md) | High | Deployment / rollback failure |
| [RB-009](./RB-009-secret-exposure.md) | Critical | Secret/API key exposure |
| [RB-010](./RB-010-ransomware.md) | Critical | Ransomware / data encryption attack |

---

## Common Procedures

### Getting Help
- **On-call**: Check `docs/ONCALL.md` for current rotation
- **Escalation**: See `docs/ESCALATION.md`
- **Communication**: Use `#incidents` channel (Slack/Discord/Matrix)

### Common Commands
```bash
# Check service health
curl -f http://localhost:8000/health

# Check logs
docker-compose logs -f backend --tail=100
docker-compose logs -f frontend --tail=100

# Restart services
docker-compose restart backend
docker-compose restart frontend

# Check database
docker-compose exec postgres pg_isready -U postgres
```

---

## Severity Definitions

| Level | Response Time | Description |
|-------|---------------|-------------|
| **Critical (P0)** | 15 min | Data loss, security breach, complete outage |
| **High (P1)** | 1 hour | Major feature down, significant user impact |
| **Medium (P2)** | 4 hours | Degraded performance, partial feature loss |
| **Low (P3)** | 24 hours | Minor issue, workaround exists |

---

## Post-Incident Process

1. **Resolve** - Fix the immediate issue
2. **Document** - Fill out incident report template
3. **Review** - Blameless postmortem within 48 hours
4. **Action Items** - Create GitHub issues for preventive measures
5. **Update Runbooks** - Improve procedures based on lessons learned

---

## Incident Report Template

```markdown
# Incident Report: [INC-YYYYMMDD-XXX]

**Date**: YYYY-MM-DD
**Duration**: X hours Y minutes
**Severity**: P0/P1/P2/P3
**Status**: Resolved / Monitoring / Investigating

## Summary
Brief description of what happened.

## Timeline
- HH:MM - Detection
- HH:MM - Investigation started
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Service restored

## Root Cause
Technical explanation of why it happened.

## Impact
- Users affected: X
- Data loss: Yes/No
- Downtime: X minutes

## Resolution
What was done to fix it.

## Action Items
- [ ] Preventive measure 1
- [ ] Preventive measure 2

## Lessons Learned
What we learned and how to prevent recurrence.
```
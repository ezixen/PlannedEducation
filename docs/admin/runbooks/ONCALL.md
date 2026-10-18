# On-Call Rotation - Free/Open-Source Only

**Project**: PlannedEducation
**Team Size**: 1 (solo founder) + community contributors
**Timezone**: UTC (adjust as needed)

---

## Current Rotation

| Week Starting | Primary On-Call | Secondary (Backup) |
|---------------|-----------------|-------------------|
| 2026-10-12    | ezixen          | Community (GitHub Issues) |
| 2026-10-19    | ezixen          | Community (GitHub Issues) |
| 2026-10-26    | ezixen          | Community (GitHub Issues) |
| 2026-11-02    | ezixen          | Community (GitHub Issues) |

---

## On-Call Responsibilities

### Primary On-Call
- **Response Time**: 15 minutes for P0, 1 hour for P1
- **Availability**: Must be reachable during assigned week
- **Tools**: GitHub notifications, email, phone (if configured)
- **Actions**: 
  - Acknowledge alerts within response time
  - Follow runbooks for diagnosis
  - Deploy fixes or workarounds
  - Update incident status in GitHub Issues
  - Communicate status to stakeholders

### Secondary (Backup)
- **Role**: Escalation point if primary unavailable
- **Activation**: If primary doesn't respond within 30 minutes (P0) or 2 hours (P1)
- **Community**: GitHub Issues monitored by contributors

---

## Contact Methods

| Method | Primary | Secondary |
|--------|---------|-----------|
| GitHub | @ezixen (notifications on) | GitHub Issues |
| Email | Configured in GitHub | N/A |
| Phone | Private (if shared) | N/A |

---

## Handoff Procedure

**Friday 17:00 UTC** (or agreed time):
1. Outgoing on-call creates GitHub Issue "On-Call Handoff - Week of YYYY-MM-DD"
2. Documents:
   - Active incidents (if any)
   - Known issues / watch items
   - Upcoming deployments/maintenance
   - Any context needed
3. Incoming on-call acknowledges and confirms availability

---

## Out-of-Hours Coverage

- **Solo founder**: Best effort outside business hours
- **Community**: GitHub Issues monitored asynchronously
- **Critical P0**: Will respond if awake/available
- **Non-critical**: Next business day

---

## On-Call Checklist (Start of Week)

- [ ] Verify GitHub notifications enabled for PlannedEducation repo
- [ ] Check current open incidents
- [ ] Review recent alerts (Prometheus/Grafana)
- [ ] Confirm backup/restore drill schedule
- [ ] Verify deployment pipeline access
- [ ] Update status in team communication channel

---

## On-Call Checklist (End of Week)

- [ ] Handoff issue created and acknowledged
- [ ] All active incidents documented
- [ ] Any new runbook updates noted
- [ ] Post-incident reviews completed for incidents this week
# Escalation Procedures - Free/Open-Source Only

**Project**: PlannedEducation
**Team Size**: 1 (solo founder) + community contributors

---

## Escalation Levels

| Level | Trigger | Response Time | Who | Actions |
|-------|---------|---------------|-----|---------|
| **L1 - Primary** | Alert fires | 15 min (P0), 1 hr (P1) | Primary On-Call | Acknowledge, diagnose, fix |
| **L2 - Secondary** | L1 no response | 30 min (P0), 2 hr (P1) | Secondary / Community | Take over, notify L1 |
| **L3 - Community** | L2 no response | 1 hr (P0), 4 hr (P1) | GitHub Issues / Contributors | Public issue, coordinate fix |
| **L4 - External** | Security breach / Legal | Immediate | Authorities / Legal | Legal compliance, disclosure |

---

## Escalation Triggers

### Automatic (Alertmanager)
- **Critical alerts** (severity=critical, burn_rate=fast): Page primary immediately
- **Warning alerts** (severity=warning, burn_rate=slow): Notify primary, escalate after 1 hour
- **Security alerts** (component=security): Page primary + secondary immediately
- **AI cost alerts** (component=ai_cost): Notify primary, escalate after 30 min

### Manual (Human-initiated)
- On-call cannot resolve within 2 hours
- Incident affects > 50% of users
- Data breach suspected
- Legal/regulatory inquiry received
- Media inquiry received

---

## Communication Channels

| Channel | Purpose | Access |
|---------|---------|--------|
| GitHub Issues | Primary incident tracking | Public |
| GitHub Discussions | Community coordination | Public |
| Email | Direct notifications | Private |
| Phone/SMS | Critical P0 only | Private (if shared) |

---

## Escalation Procedures

### P0 - Critical (Data loss, Security breach, Complete outage)

1. **T+0**: Alert fires → Primary paged
2. **T+15 min**: If no ack → Secondary paged
3. **T+30 min**: If no ack → GitHub Issue created with "P0-INCIDENT" label, community notified
4. **T+1 hr**: If no resolution → External notification (if security/legal)
5. **Continuous**: Status updates every 30 min in GitHub Issue

### P1 - High (Major feature down, Significant user impact)

1. **T+0**: Alert fires → Primary notified
2. **T+1 hr**: If no ack → Secondary notified
3. **T+2 hr**: If no ack → GitHub Issue created with "P1-INCIDENT" label
4. **T+4 hr**: If no resolution → Community coordination
5. **Updates**: Every 1 hour in GitHub Issue

### P2 - Medium (Degraded performance, Partial feature loss)

1. **T+0**: Alert fires → Primary notified
2. **T+4 hr**: If no ack → Secondary notified
3. **T+8 hr**: If no ack → GitHub Issue created with "P2-INCIDENT" label
4. **Updates**: Every 4 hours in GitHub Issue

### P3 - Low (Minor issue, Workaround exists)

1. **T+0**: Alert fires → Primary notified
2. **T+24 hr**: If no ack → GitHub Issue created with "P3-INCIDENT" label
3. **Resolution**: Next sprint / maintenance window

---

## Security Incident Escalation

### Data Breach / PII Exposure (RB-004)
1. **Immediate**: Contain (revoke keys, disable endpoints)
2. **T+15 min**: Legal counsel notification (if available)
3. **T+1 hr**: Regulatory notification prep (GDPR 72hr, FERPA, COPPA)
4. **T+4 hr**: User notification draft
5. **T+24 hr**: Public disclosure (if required)

### Secret Exposure (RB-009)
1. **Immediate**: Rotate exposed secrets
2. **T+15 min**: Audit access logs for misuse
3. **T+1 hr**: Deploy rotated secrets
4. **T+4 hr**: Verify no unauthorized access

### Ransomware (RB-010)
1. **Immediate**: Isolate affected systems
2. **T+15 min**: Activate backup restore procedure
3. **T+1 hr**: Law enforcement notification
4. **T+4 hr**: Stakeholder communication

---

## External Escalation Contacts

| Organization | When to Contact | Contact Info |
|--------------|-----------------|--------------|
| GitHub Security | Supply chain compromise | security@github.com |
| Cloudflare | DDoS / WAF issues | Cloudflare dashboard |
| Domain Registrar | Domain hijacking | Registrar support |
| Law Enforcement | Ransomware, data breach | Local cybercrime unit |
| Data Protection Authority | GDPR breach | National DPA (72hr) |

---

## Post-Escalation

1. **Incident Report**: Complete within 48 hours
2. **Blameless Postmortem**: Schedule within 1 week
3. **Action Items**: Create GitHub Issues for preventive measures
4. **Runbook Updates**: Improve procedures based on lessons learned
5. **Runbook Review**: Quarterly review of all escalation procedures

---

## Escalation Matrix Summary

```
Alert Fires
    │
    ▼
Primary On-Call (15min/1hr)
    │
    ├─ Acknowledged → Diagnose → Fix → Resolve
    │
    └─ No Response (30min/2hr)
         │
         ▼
    Secondary / Community
         │
         ├─ Takes Over → Diagnose → Fix → Resolve
         │
         └─ No Response (1hr/4hr)
              │
              ▼
         GitHub Issue + Community Coordination
              │
              ├─ Community Fix → Resolve
              │
              └─ External Escalation (Security/Legal)
                   │
                   ▼
              Authorities / Legal Counsel
```
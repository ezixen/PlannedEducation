# RB-004: Suspected Data Breach / PII Exposure

**Severity**: Critical (P0)
**Response Time**: 15 minutes
**Owner**: Security On-Call + Backend On-Call

---

## Symptoms
- Unusual database queries in logs (bulk SELECT * from users/submissions)
- Reports of student data appearing externally
- Anomalous API access patterns (bulk downloads, unusual IPs)
- Alert from monitoring: unusual data egress
- Student/parent reports of data appearing where it shouldn't

---

## Immediate Containment (First 15 minutes)

### 1. Revoke Compromised Credentials (5 minutes)
```bash
# Rotate JWT secret immediately
# Update JWT_SECRET_KEY in environment
# Restart all backend instances
docker-compose restart backend

# Rotate AI_KEY_MASTER_SECRET if AI keys potentially exposed
# Update AI_KEY_MASTER_SECRET, restart backend
```

### 2. Block Suspicious IPs (5 minutes)
```bash
# Add to Cloudflare/NGINX blocklist
# Or at application level in middleware
```

### 3. Enable Enhanced Logging (5 minutes)
```bash
# Temporarily increase log level to DEBUG
# Ensure audit logs are being captured
```

---

## Investigation (Next 30 minutes)

### 1. Check Audit Logs
```bash
# Search for suspicious patterns
grep -i "select.*from.*users\|select.*from.*submissions" /var/log/plannededucation/*.log
grep -i "bulk\|export\|download.*all" /var/log/plannededucation/*.log
```

### 2. Check Access Patterns
```bash
# Look for:
# - Single IP making many requests
# - Requests outside business hours
# - Successful auth from unusual locations
# - API keys used from unusual IPs
```

### 3. Check Anonymizer API Access
```bash
# Check who accessed /anonymizer/exams/*/submissions
# Verify only authorized teachers accessed their own exams
```

---

## Assessment

### Determine Scope
| Question | Yes/No | Notes |
|----------|--------|-------|
| Was PII exposed? (names, emails, grades) | | |
| Was data exfiltrated? (bulk download) | | |
| Are credentials compromised? | | |
| Is the breach ongoing? | | |
| Regulatory notification required? (GDPR, FERPA) | | |

---

## Notification Requirements

### If PII Exposed (GDPR/FERPA)
- **72 hours**: Notify supervisory authority (GDPR Art. 33)
- **Without undue delay**: Notify affected individuals (GDPR Art. 34)
- **FERPA**: Notify eligible students/parents

### Internal
- [ ] Notify security team lead
- [ ] Notify legal/compliance
- [ ] Notify executive leadership
- [ ] Document in incident tracker

---

## Eradication & Recovery

### 1. Rotate All Secrets
```bash
# JWT_SECRET_KEY
# AI_KEY_MASTER_SECRET
# Database passwords
# Google OAuth client secret (if compromised)
# Any API keys in environment
```

### 2. Force Re-authentication
```bash
# Invalidate all refresh tokens
# Force all users to re-login
# This happens automatically with new JWT_SECRET_KEY
```

### 3. Verify Data Integrity
```bash
# Check for unauthorized data modifications
# Compare row counts with last known good backup
# Verify no unauthorized admin accounts created
```

---

## Post-Incident

### Required Actions
- [ ] Full incident report within 24 hours
- [ ] Legal review for notification requirements
- [ ] Forensic analysis (preserve logs, disk images)
- [ ] Security audit of all access controls
- [ ] Penetration test if not done recently

### Preventive Measures
- [ ] Implement rate limiting on anonymizer API
- [ ] Add IP allowlisting for admin endpoints
- [ ] Enable database audit logging (pgaudit)
- [ ] Implement data loss prevention (DLP) scanning
- [ ] Regular secret rotation schedule
- [ ] Security awareness training for team

---

## Communication Template

### Internal (Slack/Email)
```
🚨 SECURITY INCIDENT - DATA BREACH SUSPECTED
Incident: INC-YYYYMMDD-XXX
Status: CONTAINING / INVESTIGATING / RESOLVED
Severity: P0
Lead: @security-lead

Summary: [Brief description]
Impact: [Users/data affected]
Actions: [Containment steps taken]
Next Update: [Time]
```

### External (if required)
```
Subject: Important Security Notice - PlannedEducation

Dear [User],

We are writing to inform you of a security incident that may have affected your data...
[Standard breach notification template per GDPR/FERPA]
```

---

## Post-Incident Checklist
- [ ] Incident report completed
- [ ] Legal review completed
- [ ] Affected users notified (if required)
- [ ] Regulatory notifications sent (if required)
- [ ] All secrets rotated
- [ ] Access controls reviewed
- [ ] Monitoring enhanced
- [ ] Postmortem scheduled within 48 hours
- [ ] Runbook updated with lessons learned
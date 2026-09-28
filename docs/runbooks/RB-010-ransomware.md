# RB-010: Ransomware / Data Encryption Attack

**Severity**: Critical (P0)
**Response Time**: 15 minutes
**Owner**: Security On-Call + Infrastructure On-Call

---

## Symptoms
- Database files encrypted / inaccessible
- Ransom note in logs / file system
- Files with `.encrypted`, `.locked`, `.ransom` extensions
- Unusual CPU/disk activity on database server
- Backup files also encrypted
- Ransom demand message

---

## Immediate Containment (First 15 minutes)

### 1. Isolate Affected Systems (5 minutes)
```bash
# Immediately disconnect affected containers/hosts from network
docker-compose down
# Or at infrastructure level: security group / firewall rules
```

### 2. Preserve Evidence (5 minutes)
```bash
# DO NOT pay ransom - no guarantee of recovery
# DO NOT reboot - may lose encryption keys in memory
# DO NOT run antivirus - may destroy evidence

# Snapshot affected volumes if possible
# docker commit affected_container forensic-snapshot-$(date +%s)
```

### 3. Alert Team (5 minutes)
```bash
# Notify security lead, infrastructure lead, legal
# Start incident bridge call
```

---

## Investigation (Next 30 minutes)

### 1. Identify Entry Point
| Vector | Check |
|--------|-------|
| Phishing email | Check email logs, user reports |
| Vulnerable service | Check exposed ports, CVEs |
| Compromised credentials | Check auth logs, VPN logs |
| Supply chain | Check dependencies, CI/CD |
| Insider threat | Check access logs |

### 2. Assess Damage Scope
| System | Status | Encrypted? |
|--------|--------|------------|
| PostgreSQL data | | |
| Redis data | | |
| Application code | | |
| Backups | | |
| Logs | | |
| Config/secrets | | |

---

## Recovery (Priority Order)

### 1. Restore from Clean Backups (Primary)
```bash
# Verify backups are NOT encrypted
# Test restore in isolated environment first

# PostgreSQL
./scripts/backup_restore.sh restore ./backups/plannededucation_pg_20260928_120000.sql.gz

# Redis
# Restore from RDB/AOF if available
```

### 2. Rebuild from Source (If Backups Compromised)
```bash
# Rebuild containers from known good images
docker-compose pull
docker-compose build --no-cache
docker-compose up -d

# Recreate database schema
docker-compose exec backend alembic upgrade head

# Re-create admin users if needed
```

### 3. Verify Data Integrity
```bash
# Check row counts match expectations
# Verify no unauthorized users/records
# Check for backdoors (new admin users, scheduled jobs)
```

---

## Post-Recovery Hardening

### Immediate (Before Restoring Service)
- [ ] Rotate ALL secrets (see RB-009)
- [ ] Patch all systems (OS, Docker, PostgreSQL, Redis)
- [ ] Close unnecessary ports
- [ ] Enable firewall rules (deny by default)
- [ ] Enable fail2ban / SSH hardening
- [ ] Disable root SSH login
- [ ] Enable 2FA for all admin access

### Short-term (Within 24 hours)
- [ ] Implement WAF (Cloudflare free tier)
- [ ] Enable database audit logging (pgaudit)
- [ ] Set up file integrity monitoring (AIDE/Tripwire)
- [ ] Implement network segmentation
- [ ] Review and harden Docker images

### Long-term
- [ ] Regular penetration testing
- [ ] Implement zero-trust network
- [ ] Regular backup restore drills
- [ ] Security awareness training
- [ ] Incident response tabletop exercises

---

## Legal & Compliance

### Reporting Requirements
- **Law enforcement**: Report to local cybercrime unit
- **GDPR**: 72-hour notification if personal data affected
- **Insurance**: Notify cyber insurance provider
- **Regulators**: Industry-specific notifications

### Evidence Preservation
- [ ] Preserve disk images of affected systems
- [ ] Preserve logs (ship to immutable storage)
- [ ] Document timeline
- [ ] Chain of custody for evidence

---

## Communication

### Internal
```
🚨 RANSOMWARE ATTACK - SERVICE OFFLINE
Incident: INC-YYYYMMDD-XXX
Status: CONTAINED / RECOVERING
Impact: [Systems affected]
Recovery: Restoring from backup / Rebuilding
ETA: [Time]
```

### External (if customer data affected)
- Follow RB-004 data breach notification
- Transparent communication about what happened
- What data was/wasn't affected
- Steps taken to prevent recurrence

---

## Post-Incident

### Required
- [ ] Full forensic analysis
- [ ] Root cause analysis
- [ ] Complete incident report
- [ ] Legal review
- [ ] Insurance claim (if applicable)

### Preventive
- [ ] Implement all hardening measures
- [ ] Regular backup restore tests (monthly)
- [ ] Penetration testing (quarterly)
- [ ] Security awareness training
- [ ] Tabletop exercise for ransomware scenario
- [ ] Cyber insurance review

---

## Decision: Pay or Not Pay?

**DO NOT PAY** - Official guidance from FBI, CISA, NCSC:
- No guarantee of decryption
- Funds criminal activity
- May be illegal (sanctions)
- Encourages future attacks
- Decryptors often don't work

**Instead**: Restore from backups, rebuild, harden.
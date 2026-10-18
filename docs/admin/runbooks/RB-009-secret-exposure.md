# RB-009: Secret / API Key Exposure

**Severity**: Critical (P0)
**Response Time**: 15 minutes
**Owner**: Security On-Call + Backend On-Call

---

## Symptoms
- Secret found in Git history / public repo
- API key posted in chat / issue / log
- Alert from GitHub secret scanning / gitleaks
- Developer accidentally committed `.env` file
- API key visible in CI logs / Docker image

---

## Immediate Containment (First 15 minutes)

### 1. Rotate Exposed Secret Immediately (5 minutes)
```bash
# For each exposed secret type:

# JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_hex(64))"
# Update in all environments, restart all backends

# AI_KEY_MASTER_SECRET
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Update, restart backend (re-encrypts AI keys on next access)

# Database password
# Generate new, update postgres, update all services

# Google OAuth client secret
# Google Cloud Console > Credentials > Regenerate secret
# Update all services

# Any API keys (Gemini, OpenRouter, etc.)
# Provider console > Regenerate key
# Update teacher settings / environment
```

### 2. Remove from Git History (5 minutes)
```bash
# If committed to git, use BFG Repo-Cleaner or git-filter-repo
# DO NOT just delete file - history still contains secret

# Install BFG
# java -jar bfg.jar --delete-files .env
# git reflog expire --expire=now --all && git gc --prune=now --aggressive

# OR git-filter-repo
# pip install git-filter-repo
# git filter-repo --path .env --invert-paths
```

### 3. Force Push Cleaned History (5 minutes)
```bash
# Force push to all remotes
git push origin --force --all
git push origin --force --tags

# Notify team to re-clone
```

---

## Investigation (Next 30 minutes)

### 1. Assess Exposure Scope
| Question | Yes/No | Notes |
|----------|--------|-------|
| Was secret in public repo? | | |
| Was secret in CI logs? | | |
| Was secret in Docker image? | | |
| Was secret shared in chat/email? | | |
| How long was it exposed? | | |

### 2. Check for Abuse
```bash
# Check API usage for rotated keys
# Check database for unauthorized access
# Check audit logs for unusual activity
```

---

## Recovery

### 1. Verify All Secrets Rotated
- [ ] JWT_SECRET_KEY
- [ ] AI_KEY_MASTER_SECRET
- [ ] Database passwords
- [ ] Google OAuth client secret
- [ ] All AI provider API keys
- [ ] Any other service credentials

### 2. Verify Clean History
```bash
# Scan repo for secrets
gitleaks detect --source . --verbose
```

### 3. Force Re-authentication
```bash
# New JWT_SECRET_KEY automatically invalidates all tokens
# Users must re-login (expected)
```

---

## Post-Incident

### Required
- [ ] Incident report
- [ ] Confirm all secrets rotated
- [ ] Confirm git history cleaned
- [ ] Team notified to re-clone repo
- [ ] CI/CD secrets updated in GitHub Settings

### Preventive
- [ ] Add pre-commit hook for secret scanning
- [ ] Add gitleaks to CI (already done)
- [ ] Add `.env` to `.gitignore` (verify)
- [ ] Use GitHub secret scanning (if public repo)
- [ ] Regular secret rotation schedule
- [ ] Developer training on secret handling

---

## Communication

### Internal
```
🚨 SECRET EXPOSURE - IMMEDIATE ROTATION REQUIRED
Incident: INC-YYYYMMDD-XXX
Secrets Rotated: [list]
Git History Cleaned: Yes/No
Team Action: Re-clone repo, update local .env
```

### External (if customer data affected)
- Follow RB-004 data breach notification process
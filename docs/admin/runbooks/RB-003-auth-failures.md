# RB-003: Authentication Failures / Login Issues

**Severity**: High (P1)
**Response Time**: 1 hour
**Owner**: Backend On-Call

---

## Symptoms
- Users cannot log in via Google SSO
- "Invalid credentials" errors for valid users
- JWT validation failures
- 401 Unauthorized on valid tokens
- Google OAuth callback failures

---

## Diagnosis Steps

### 1. Check Google OAuth Status (5 minutes)
```bash
# Test Google OAuth endpoint
curl -X POST http://localhost:8000/auth/google \
  -H "Content-Type: application/json" \
  -d '{"token": "test"}'
# Should return 401 (invalid token) not 500/503
```

### 2. Check JWT Configuration (5 minutes)
```bash
# Verify JWT_SECRET_KEY is set
docker-compose exec backend env | grep JWT_SECRET

# Test token creation/validation
docker-compose exec backend python -c "
from src.plannededucation.api.auth import create_access_token, verify_refresh_token
token = create_access_token({'sub': 'test@test.com'})
print('Token:', token[:50])
"
```

### 3. Check Google OAuth Config (5 minutes)
```bash
# Verify GOOGLE_CLIENT_ID is set
docker-compose exec backend env | grep GOOGLE_CLIENT

# Check Google Cloud Console: APIs & Services > Credentials
# - Authorized redirect URIs correct?
# - OAuth consent screen published?
```

---

## Common Causes & Fixes

| Cause | Detection | Fix |
|-------|-----------|-----|
| JWT_SECRET_KEY missing/changed | 500 on /auth/me, token validation fails | Set JWT_SECRET_KEY, restart backend |
| GOOGLE_CLIENT_ID missing | 503 on /auth/google | Set GOOGLE_CLIENT_ID, restart backend |
| Google OAuth redirect URI mismatch | 400 on callback | Update Google Cloud Console redirect URIs |
| Token expired | 401 on valid requests | User must re-login (normal) |
| Clock skew | Tokens valid but rejected | Sync server time (NTP) |
| Database connection failed | 500 on auth endpoints | Check DB (see RB-001) |

---

## Quick Fixes

### Rotate JWT Secret (if compromised)
```bash
# Generate new secret
python -c "import secrets; print(secrets.token_hex(64))"

# Update in environment, restart all backends
# NOTE: This logs out ALL users
```

### Fix Google OAuth Redirect
```bash
# In Google Cloud Console:
# APIs & Services > Credentials > OAuth 2.0 Client IDs
# Authorized redirect URIs: https://yourdomain.com/auth/callback
# (or http://localhost:5173/auth/callback for dev)
```

---

## Verification
- [ ] `POST /auth/google` returns 401 (not 500/503)
- [ ] Valid Google token returns access + refresh tokens
- [ ] `GET /auth/me` works with valid token
- [ ] Refresh token endpoint works

---

## Post-Incident
- [ ] Document root cause
- [ ] Add monitoring for auth endpoint errors
- [ ] Add alert for JWT_SECRET_KEY missing
- [ ] Document secret rotation procedure
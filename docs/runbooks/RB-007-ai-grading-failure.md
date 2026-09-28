# RB-007: AI Grading Service Failures

**Severity**: Medium (P2)
**Response Time**: 4 hours
**Owner**: Backend On-Call

---

## Symptoms
- Anonymizer API returns errors
- AI grading jobs fail silently
- Teachers cannot fetch submissions for grading
- "AI service unavailable" errors
- Grades not posting back to system

---

## Diagnosis Steps

### 1. Check Anonymizer Endpoints (5 minutes)
```bash
# Test anonymizer submissions endpoint
curl -H "Authorization: Bearer TEACHER_TOKEN" \
  http://localhost:8000/anonymizer/exams/EXAM_ID/submissions
# Should return anonymized submissions
```

### 2. Check AI Provider Config (5 minutes)
```bash
# Check teacher's AI settings
docker-compose exec backend python -c "
from src.plannededucation.api import database, models
db = next(database.get_db())
teacher = db.query(models.User).filter(models.User.id == TEACHER_ID).first()
print('ai_provider:', teacher.ai_provider)
print('ai_model_name:', teacher.ai_model_name)
print('ai_base_url:', teacher.ai_base_url)
print('has_api_key:', bool(teacher.ai_api_key_encrypted))
"
```

### 3. Check Crypto/Decryption (5 minutes)
```bash
# Test AI key decryption
docker-compose exec backend python -c "
from src.plannededucation.api import crypto, database, models
db = next(database.get_db())
teacher = db.query(models.User).filter(models.User.id == TEACHER_ID).first()
if teacher.ai_api_key_encrypted:
    decrypted = crypto.decrypt_api_key(teacher.ai_api_key_encrypted)
    print('Decrypted:', decrypted[:10] + '...' if decrypted else 'FAILED')
else:
    print('No API key set')
"
```

---

## Common Causes & Fixes

| Cause | Detection | Fix |
|-------|-----------|-----|
| No AI provider configured | `ai_provider` is NULL | Teacher must configure in Settings |
| Invalid API key | Decryption fails or API returns 401 | Teacher must update API key in Settings |
| AI provider rate limited | 429 errors from provider | Wait, add exponential backoff |
| AI provider down | 5xx from provider | Check provider status page |
| Presidio not installed | ImportError in logs | `pip install presidio-analyzer presidio-anonymizer` |
| PII scrubbing fails | Errors in anonymizer logs | Check Presidio models downloaded |

---

## Quick Fixes

### Install Presidio (if missing)
```bash
docker-compose exec backend pip install presidio-analyzer presidio-anonymizer
# Download models
docker-compose exec backend python -c "
from presidio_analyzer import AnalyzerEngine
AnalyzerEngine()  # Triggers model download
"
```

### Test AI Provider Directly
```bash
# Test Gemini
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

### Re-encrypt AI Key (if master key rotated)
```bash
# Teacher must re-enter API key in Settings UI
# Or admin can re-encrypt via script
```

---

## Verification
- [ ] `GET /anonymizer/exams/EXAM_ID/submissions` returns data
- [ ] PII scrubbing works (no real names in output)
- [ ] `POST /anonymizer/submissions/ID/grades` accepts grades
- [ ] Teacher can configure AI provider in Settings

---

## Post-Incident
- [ ] Add AI provider health check endpoint
- [ ] Add circuit breaker for external AI calls
- [ ] Add retry logic with exponential backoff
- [ ] Monitor AI provider latency/errors
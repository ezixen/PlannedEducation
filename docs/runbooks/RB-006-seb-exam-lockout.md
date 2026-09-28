# RB-006: Students Locked Out of SEB Exam

**Severity**: High (P1)
**Response Time**: 1 hour
**Owner**: Backend On-Call

---

## Symptoms
- Students cannot start exam via SEB
- "Safe Exam Browser is required" errors
- SEB config download fails
- Exam start endpoint returns 403/409
- Students report "exam already started" incorrectly

---

## Diagnosis Steps

### 1. Check SEB Config Endpoint (5 minutes)
```bash
# Test SEB config generation
curl -H "Authorization: Bearer TEACHER_TOKEN" \
  http://localhost:8000/exams/EXAM_ID/seb-config
# Should return .seb file download
```

### 2. Check Exam Start Endpoint (5 minutes)
```bash
# Test exam start with dev bypass
curl -X POST -H "Authorization: Bearer STUDENT_TOKEN" \
  http://localhost:8000/exams/EXAM_ID/start
# Should return exam questions
```

### 3. Check SEB Config Key (5 minutes)
```bash
# Verify exam has seb_config_key set
docker-compose exec backend python -c "
from src.plannededucation.api import database, models
db = next(database.get_db())
exam = db.query(models.Exam).filter(models.Exam.id == EXAM_ID).first()
print('seb_config_key:', exam.seb_config_key)
"
```

---

## Common Causes & Fixes

| Cause | Detection | Fix |
|-------|-----------|-----|
| No SEB config key set | `seb_config_key` is NULL | Teacher must generate SEB config first |
| Dev bypass not enabled | 403 "SEB required" in dev | Set `ALLOW_DEV_SEB_BYPASS=true` |
| Config key mismatch | 403 "Hash mismatch" | Regenerate SEB config, re-download |
| Exam already started | 400 "Exam already started" | Check submissions table, allow retry if needed |
| Wrong exam ID | 404 "Exam not found" | Verify exam_id in URL |

---

## Quick Fixes

### Enable Dev Bypass (development only)
```bash
# In docker-compose.yml backend environment
ALLOW_DEV_SEB_BYPASS: "true"
PLANNED_EDUCATION_ENV: "development"
docker-compose restart backend
```

### Regenerate SEB Config
```bash
# Teacher downloads new .seb file from exam editor
# Students use new .seb file
```

### Allow Exam Retry (if student crashed)
```bash
# Delete incomplete submission
docker-compose exec backend python -c "
from src.plannededucation.api import database, models
db = next(database.get_db())
sub = db.query(models.ExamSubmission).filter(
    models.ExamSubmission.exam_id == EXAM_ID,
    models.ExamSubmission.student_id == STUDENT_ID
).first()
if sub and not sub.completed_at:
    db.delete(sub)
    db.commit()
    print('Deleted incomplete submission')
"
```

---

## Verification
- [ ] Teacher can download .seb config
- [ ] Student can start exam with .seb file
- [ ] Exam questions load correctly
- [ ] Chat works in SEB mode

---

## Post-Incident
- [ ] Document root cause
- [ ] Add SEB config validation to teacher UI
- [ ] Add student-facing error messages for common issues
- [ ] Test SEB flow end-to-end
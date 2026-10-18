# RB-005: WebSocket / Chat Service Failures

**Severity**: High (P1)
**Response Time**: 1 hour
**Owner**: Backend On-Call

---

## Symptoms
- Students cannot connect to exam chat
- "WebSocket connection failed" errors
- Messages not delivering between teacher/students
- Chat shows "disconnected" status
- WebSocket handshake failures (400/401/1008)

---

## Diagnosis Steps

### 1. Check WebSocket Endpoint (5 minutes)
```bash
# Test WebSocket endpoint directly
wscat -c "ws://localhost:8000/chat/exam/1?token=VALID_TOKEN"
# Should connect and echo messages
```

### 2. Check Backend Logs (5 minutes)
```bash
docker-compose logs backend --tail=100 | grep -i "websocket\|chat\|ws"
```

### 3. Check Redis (if enabled) (5 minutes)
```bash
docker-compose exec redis redis-cli ping
docker-compose exec redis redis-cli PUBSUB CHANNELS
```

---

## Common Causes & Fixes

| Cause | Detection | Fix |
|-------|-----------|-----|
| Invalid/expired token | 1008 close code, "Invalid token" | User must re-login |
| Exam not found | 1008 "Exam not found" | Verify exam_id exists |
| User not authorized | 1008 "Not authorised" | User must be teacher owner or have active submission |
| Redis unavailable | Pub/Sub errors in logs | Check Redis container, restart if needed |
| Connection pool exhausted | "too many connections" | Increase worker connections |
| Message too large | 1009 close code | Client must respect 2KB limit |

---

## Quick Fixes

### Restart Backend (clears connections)
```bash
docker-compose restart backend
```

### Restart Redis (if Pub/Sub issues)
```bash
docker-compose restart redis
```

### Check USE_REDIS_CHAT Flag
```bash
# In docker-compose.yml backend environment
USE_REDIS_CHAT: "true"  # or "false" for single-worker
```

---

## Verification
- [ ] `wscat` connects successfully with valid token
- [ ] Messages broadcast to all participants
- [ ] Teacher and student can exchange messages
- [ ] No errors in backend logs for 5 minutes

---

## Post-Incident
- [ ] Add WebSocket connection metrics
- [ ] Add alert for WebSocket error rate
- [ ] Document token refresh flow for long exams
- [ ] Test multi-worker scenario
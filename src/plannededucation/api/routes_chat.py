import asyncio
import contextlib
import json
import os

import jwt  # PyJWT for JWT encoding/decoding
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from . import auth, database, models

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Redis Pub/Sub Manager (for multi-worker deployments) ─────────────────────

class RedisPubSubManager:
    """
    Redis-backed Pub/Sub for cross-worker WebSocket message broadcasting.
    Falls back to in-memory if Redis is not configured.
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis = None
        self._pubsub = None
        self._listener_task = None
        self._local_connections: dict[str, list[dict]] = {}  # exam_id -> [{"ws": ws, "user": user}]
        self._running = False

    async def _get_redis(self):
        """Lazy Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    async def start(self):
        """Start the Redis listener."""
        redis = await self._get_redis()
        if not redis:
            return  # Fall back to in-memory only
        self._running = True
        self._pubsub = redis.pubsub()
        await self._pubsub.subscribe("chat:broadcast")
        self._listener_task = asyncio.create_task(self._listen())

    async def stop(self):
        """Stop the Redis listener."""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener_task
        if self._pubsub:
            await self._pubsub.unsubscribe("chat:broadcast")
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()

    async def _listen(self):
        """Listen for messages on Redis channel and broadcast locally."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self._broadcast_local(data["exam_id"], data["payload"])
        except asyncio.CancelledError:
            pass
        except Exception:
            pass  # Log in production

    async def _broadcast_local(self, exam_id: str, payload: str):
        """Broadcast to local connections only."""
        connections = self._local_connections.get(exam_id, [])
        dead = []
        for conn in connections:
            try:
                await conn["websocket"].send_text(payload)
            except Exception:
                dead.append(conn)
        for d in dead:
            if exam_id in self._local_connections:
                self._local_connections[exam_id].remove(d)

    async def connect(self, websocket, exam_id: str, user):
        """Register a local connection."""
        if exam_id not in self._local_connections:
            self._local_connections[exam_id] = []
        self._local_connections[exam_id].append({"websocket": websocket, "user": user})

    def disconnect(self, websocket, exam_id: str):
        """Remove a local connection."""
        if exam_id in self._local_connections:
            self._local_connections[exam_id] = [
                c for c in self._local_connections[exam_id] if c["websocket"] is not websocket
            ]

    async def broadcast_to_exam(self, message: str, exam_id: str, sender_name: str):
        """Broadcast to all workers via Redis, then locally."""
        payload = json.dumps({"sender": sender_name, "message": message})

        # Publish to Redis for other workers
        redis = await self._get_redis()
        if redis:
            with contextlib.suppress(Exception):
                await redis.publish(
                    "chat:broadcast",
                    json.dumps({"exam_id": exam_id, "payload": payload}),
                )

        # Always broadcast locally
        await self._broadcast_local(exam_id, payload)


# ── Connection Manager (auto-detects Redis) ──────────────────────────────────

class ConnectionManager:
    """
    Unified connection manager that uses Redis Pub/Sub when available,
    falls back to in-memory for single-process deployments.
    """

    def __init__(self):
        self._redis_manager = RedisPubSubManager()
        self._use_redis = os.getenv("USE_REDIS_CHAT", "false").lower() == "true"

    async def start(self):
        if self._use_redis:
            await self._redis_manager.start()

    async def stop(self):
        if self._use_redis:
            await self._redis_manager.stop()

    async def connect(self, websocket, exam_id: str, user):
        if self._use_redis:
            await self._redis_manager.connect(websocket, exam_id, user)
        else:
            # In-memory fallback
            if not hasattr(self, '_local_connections'):
                self._local_connections = {}
            if exam_id not in self._local_connections:
                self._local_connections[exam_id] = []
            self._local_connections[exam_id].append({"websocket": websocket, "user": user})

    def disconnect(self, websocket, exam_id: str):
        if self._use_redis:
            self._redis_manager.disconnect(websocket, exam_id)
        else:
            if hasattr(self, '_local_connections') and exam_id in self._local_connections:
                self._local_connections[exam_id] = [
                    c for c in self._local_connections[exam_id] if c["websocket"] is not websocket
                ]

    async def broadcast_to_exam(self, message: str, exam_id: str, sender_name: str):
        if self._use_redis:
            await self._redis_manager.broadcast_to_exam(message, exam_id, sender_name)
        else:
            # In-memory fallback
            if not hasattr(self, '_local_connections'):
                return
            connections = self._local_connections.get(exam_id, [])
            dead = []
            payload = json.dumps({"sender": sender_name, "message": message})
            for conn in connections:
                try:
                    await conn["websocket"].send_text(payload)
                except Exception:
                    dead.append(conn)
            for d in dead:
                if exam_id in self._local_connections:
                    self._local_connections[exam_id].remove(d)


manager = ConnectionManager()


# ── Auth helper ───────────────────────────────────────────────────────────────

def _get_user_from_ws_token(token: str, db: Session) -> models.User | None:
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str | None = payload.get("sub")
        if not email:
            return None
        user = db.query(models.User).filter(models.User.email == email).first()
        return user if (user and user.is_active) else None
    except jwt.exceptions.InvalidTokenError:
        return None


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/exam/{exam_id}")
async def exam_chat_endpoint(websocket: WebSocket, exam_id: str):
    await websocket.accept()

    # ── Step 1: Receive auth frame ───────────────────────────────────────────
    try:
        auth_data = await websocket.receive_text()
        auth_json = json.loads(auth_data)
        token = auth_json.get("token", "")
        if not token:
            await websocket.close(code=1008, reason="Missing token")
            return
    except Exception:
        await websocket.close(code=1008, reason="Invalid auth frame")
        return

    # ── Step 2: Validate token ───────────────────────────────────────────────
    db: Session = next(database.get_db())
    try:
        user = _get_user_from_ws_token(token, db)
        if not user:
            await websocket.close(code=1008, reason="Invalid or expired token")
            return

        # ── Step 3: Verify access to this exam room ──────────────────────────
        exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
        if not exam:
            await websocket.close(code=1008, reason="Exam not found")
            return

        # A user may join chat if they own the exam OR have an active submission
        is_owner = (exam.teacher_id == user.id)
        has_submission = (
            db.query(models.ExamSubmission)
            .filter(
                models.ExamSubmission.exam_id == exam_id,
                models.ExamSubmission.student_id == user.id,
            )
            .first()
            is not None
        )

        if not is_owner and not has_submission:
            await websocket.close(code=1008, reason="Not authorised to join this exam room")
            return

        # ── Step 4: Serve messages ───────────────────────────────────────────
        await manager.connect(websocket, exam_id, user)
        try:
            while True:
                data = await websocket.receive_text()
                # Truncate messages to 2 KB to prevent message flooding
                data = data[:2048]
                await manager.broadcast_to_exam(data, exam_id, user.full_name or user.username)
        except WebSocketDisconnect:
            manager.disconnect(websocket, exam_id)
    finally:
        db.close()

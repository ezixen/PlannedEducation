import asyncio
import contextlib
import json
import os

import jwt  # PyJWT for JWT encoding/decoding
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from . import auth, database, models, schemas
from .routes_auth import get_current_user

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
    except WebSocketDisconnect:
        return
    except Exception:
        with contextlib.suppress(Exception):
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


# ── Teacher's Lounge REST Endpoints ──────────────────────────────────────────


def _require_teacher_or_admin(current_user: models.User) -> None:
    if current_user.role not in ("teacher", "teacher_aide", "admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers, teacher's aides, and admins can access the lounge",
        )


@router.get("/lounge/messages", response_model=list[schemas.TeacherLoungeMessageResponse])
def list_lounge_messages(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """List all top-level teacher's lounge messages with their replies."""
    _require_teacher_or_admin(current_user)

    messages = (
        db.query(models.TeacherLoungeMessage)
        .filter(models.TeacherLoungeMessage.parent_id.is_(None))
        .order_by(models.TeacherLoungeMessage.is_pinned.desc(), models.TeacherLoungeMessage.created_at.desc())
        .all()
    )

    result = []
    for msg in messages:
        sender = db.query(models.User).filter(models.User.id == msg.sender_id).first()
        result.append(
            schemas.TeacherLoungeMessageResponse(
                id=msg.id,
                sender_id=msg.sender_id,
                sender_name=sender.full_name or sender.username if sender else None,
                content=msg.content,
                parent_id=msg.parent_id,
                is_pinned=msg.is_pinned,
                created_at=msg.created_at,
                updated_at=msg.updated_at,
                replies=[],
            )
        )

    # Load replies for each message
    for item in result:
        replies = (
            db.query(models.TeacherLoungeMessage)
            .filter(models.TeacherLoungeMessage.parent_id == item.id)
            .order_by(models.TeacherLoungeMessage.created_at.asc())
            .all()
        )
        item.replies = [
            schemas.TeacherLoungeMessageResponse(
                id=r.id,
                sender_id=r.sender_id,
                sender_name=(
                    db.query(models.User).filter(models.User.id == r.sender_id).first().full_name
                    or db.query(models.User).filter(models.User.id == r.sender_id).first().username
                ),
                content=r.content,
                parent_id=r.parent_id,
                is_pinned=r.is_pinned,
                created_at=r.created_at,
                updated_at=r.updated_at,
                replies=[],
            )
            for r in replies
        ]

    return result


@router.post("/lounge/messages", response_model=schemas.TeacherLoungeMessageResponse)
def create_lounge_message(
    payload: schemas.TeacherLoungeMessageCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Post a new message to the teacher's lounge."""
    _require_teacher_or_admin(current_user)

    if payload.parent_id:
        parent = db.query(models.TeacherLoungeMessage).filter(
            models.TeacherLoungeMessage.id == payload.parent_id
        ).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent message not found",
            )

    message = models.TeacherLoungeMessage(
        sender_id=current_user.id,
        parent_id=payload.parent_id,
        content=payload.content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return schemas.TeacherLoungeMessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        sender_name=current_user.full_name or current_user.username,
        content=message.content,
        parent_id=message.parent_id,
        is_pinned=message.is_pinned,
        created_at=message.created_at,
        updated_at=message.updated_at,
        replies=[],
    )


@router.put("/lounge/messages/{message_id}", response_model=schemas.TeacherLoungeMessageResponse)
def update_lounge_message(
    message_id: str,
    payload: schemas.TeacherLoungeMessageUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Update a lounge message (only the sender can edit)."""
    _require_teacher_or_admin(current_user)

    message = db.query(models.TeacherLoungeMessage).filter(
        models.TeacherLoungeMessage.id == message_id
    ).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    if message.sender_id != current_user.id and current_user.role not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the sender or an admin can edit this message",
        )

    message.content = payload.content
    db.commit()
    db.refresh(message)

    sender = db.query(models.User).filter(models.User.id == message.sender_id).first()
    return schemas.TeacherLoungeMessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        sender_name=sender.full_name or sender.username if sender else None,
        content=message.content,
        parent_id=message.parent_id,
        is_pinned=message.is_pinned,
        created_at=message.created_at,
        updated_at=message.updated_at,
        replies=[],
    )


@router.delete("/lounge/messages/{message_id}")
def delete_lounge_message(
    message_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Delete a lounge message (only the sender or an admin)."""
    _require_teacher_or_admin(current_user)

    message = db.query(models.TeacherLoungeMessage).filter(
        models.TeacherLoungeMessage.id == message_id
    ).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    if message.sender_id != current_user.id and current_user.role not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the sender or an admin can delete this message",
        )

    db.delete(message)
    db.commit()

    return {"status": "success", "message": "Message deleted"}


@router.post("/lounge/messages/{message_id}/pin")
def pin_lounge_message(
    message_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    """Pin or unpin a lounge message (teachers and admins only)."""
    _require_teacher_or_admin(current_user)

    message = db.query(models.TeacherLoungeMessage).filter(
        models.TeacherLoungeMessage.id == message_id
    ).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    message.is_pinned = not message.is_pinned
    db.commit()

    return {
        "status": "success",
        "message": f"Message {'pinned' if message.is_pinned else 'unpinned'}",
        "is_pinned": message.is_pinned,
    }

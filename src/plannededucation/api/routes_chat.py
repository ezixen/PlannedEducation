import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
from jose import jwt, JWTError
from . import auth, database, models
from sqlalchemy.orm import Session

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Connection Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    """
    In-memory connection manager. Sufficient for single-process deployments.
    For multi-worker/multi-server deployments, replace broadcast_to_exam
    with a Redis Pub/Sub publisher.
    """

    def __init__(self):
        # exam_id -> list of {"websocket": ws, "user": User}
        self.active_connections: Dict[str, List[Dict]] = {}

    async def connect(self, websocket: WebSocket, exam_id: str, user: models.User) -> None:
        if exam_id not in self.active_connections:
            self.active_connections[exam_id] = []
        self.active_connections[exam_id].append({"websocket": websocket, "user": user})

    def disconnect(self, websocket: WebSocket, exam_id: str) -> None:
        if exam_id in self.active_connections:
            self.active_connections[exam_id] = [
                c for c in self.active_connections[exam_id] if c["websocket"] is not websocket
            ]

    async def broadcast_to_exam(self, message: str, exam_id: str, sender_name: str) -> None:
        connections = self.active_connections.get(exam_id, [])
        dead: list = []
        payload = json.dumps({"sender": sender_name, "message": message})
        for conn in connections:
            try:
                await conn["websocket"].send_text(payload)
            except Exception:
                dead.append(conn)
        # Clean up dead connections
        for d in dead:
            self.active_connections[exam_id].remove(d)


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
    except JWTError:
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

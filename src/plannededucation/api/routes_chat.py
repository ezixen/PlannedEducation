from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from typing import Dict, List
import json
from jose import jwt, JWTError
from . import auth, database, models
from sqlalchemy.orm import Session

router = APIRouter(prefix="/chat", tags=["chat"])

class ConnectionManager:
    def __init__(self):
        # Maps exam_id -> list of active websockets (students + teacher)
        self.active_connections: Dict[int, List[Dict[str, any]]] = {}

    async def connect(self, websocket: WebSocket, exam_id: int, user: models.User):
        await websocket.accept()
        if exam_id not in self.active_connections:
            self.active_connections[exam_id] = []
        
        self.active_connections[exam_id].append({
            "websocket": websocket,
            "user": user
        })

    def disconnect(self, websocket: WebSocket, exam_id: int):
        if exam_id in self.active_connections:
            self.active_connections[exam_id] = [
                conn for conn in self.active_connections[exam_id] 
                if conn["websocket"] != websocket
            ]

    async def broadcast_to_exam(self, message: str, exam_id: int, sender_name: str, sender_role: str):
        if exam_id in self.active_connections:
            payload = json.dumps({
                "sender": sender_name,
                "role": sender_role,
                "message": message
            })
            for connection in self.active_connections[exam_id]:
                await connection["websocket"].send_text(payload)

manager = ConnectionManager()

def get_user_from_token(token: str, db: Session) -> models.User:
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise ValueError("Invalid token")
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            raise ValueError("User not found")
        return user
    except (JWTError, ValueError):
        return None

@router.websocket("/exam/{exam_id}")
async def exam_chat_endpoint(
    websocket: WebSocket, 
    exam_id: int
):
    await websocket.accept()
    
    # Wait for the first message to be the auth token payload
    try:
        auth_data = await websocket.receive_text()
        auth_json = json.loads(auth_data)
        token = auth_json.get("token")
        if not token:
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return
        
    db = next(database.get_db())
    try:
        user = get_user_from_token(token, db)
        if not user:
            await websocket.close(code=1008)
            return
            
        # Verify Authorization to join this exam room
        exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
        if not exam:
            await websocket.close(code=1008)
            return
            
        if user.role == "teacher" and exam.teacher_id != user.id:
            await websocket.close(code=1008) # Unauthorized teacher
            return
            
        if user.role == "student":
            # Student must have an active submission to join chat
            submission = db.query(models.ExamSubmission).filter(
                models.ExamSubmission.exam_id == exam_id,
                models.ExamSubmission.student_id == user.id
            ).first()
            if not submission:
                await websocket.close(code=1008) # Student not taking this exam
                return

        await manager.connect(websocket, exam_id, user)
        
        try:
            while True:
                data = await websocket.receive_text()
                # Broadcast the message to everyone in this exam's chat room (Teacher + Students)
                await manager.broadcast_to_exam(data, exam_id, user.full_name, user.role)
        except WebSocketDisconnect:
            manager.disconnect(websocket, exam_id)
    finally:
        db.close()


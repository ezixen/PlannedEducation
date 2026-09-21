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
    exam_id: int, 
    token: str = Query(...), 
):
    # Dependency injection doesn't work the same in WebSockets, we resolve DB manually
    db = next(database.get_db())
    user = get_user_from_token(token, db)
    
    if not user:
        await websocket.close(code=1008)
        return
        
    await manager.connect(websocket, exam_id, user)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast the message to everyone in this exam's chat room (Teacher + Students)
            await manager.broadcast_to_exam(data, exam_id, user.full_name, user.role)
    except WebSocketDisconnect:
        manager.disconnect(websocket, exam_id)
        # Optional: broadcast that the user left


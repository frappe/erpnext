"""
Communication & Chat API Router

Handles internal messaging, notifications, and communication
"""

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict
from datetime import datetime
import json

import models
import schemas
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)
    
    async def broadcast(self, message: str, company_id: str):
        for user_id, connection in self.active_connections.items():
            await connection.send_text(message)


manager = ConnectionManager()


# ============================================================================
# CHAT MESSAGES
# ============================================================================

@router.post("/messages", response_model=dict)
def send_message(
    message: schemas.ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Send a chat message"""
    
    db_message = models.ChatMessage(
        company_id=current_user.company_id,
        sender_id=current_user.id,
        recipient_id=message.recipient_id,
        channel_id=message.channel_id,
        message_text=message.message_text,
        message_type=message.message_type or "text",
        is_read=False
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    return {
        "id": db_message.id,
        "message": "Message sent successfully",
        "sent_at": db_message.created_at.isoformat() if db_message.created_at else None
    }


@router.get("/messages", response_model=List[dict])
def get_messages(
    recipient_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get chat messages"""
    
    query = db.query(models.ChatMessage).filter(
        models.ChatMessage.company_id == current_user.company_id
    )
    
    if recipient_id:
        # Direct messages between current user and recipient
        query = query.filter(
            or_(
                and_(
                    models.ChatMessage.sender_id == current_user.id,
                    models.ChatMessage.recipient_id == recipient_id
                ),
                and_(
                    models.ChatMessage.sender_id == recipient_id,
                    models.ChatMessage.recipient_id == current_user.id
                )
            )
        )
    elif channel_id:
        # Channel messages
        query = query.filter(models.ChatMessage.channel_id == channel_id)
    else:
        # All messages for current user
        query = query.filter(
            or_(
                models.ChatMessage.sender_id == current_user.id,
                models.ChatMessage.recipient_id == current_user.id
            )
        )
    
    messages = query.order_by(models.ChatMessage.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for msg in messages:
        sender = db.query(models.User).filter(models.User.id == msg.sender_id).first()
        recipient = db.query(models.User).filter(models.User.id == msg.recipient_id).first()
        
        result.append({
            "id": msg.id,
            "sender": sender.full_name if sender else "Unknown",
            "recipient": recipient.full_name if recipient else "Channel",
            "message_text": msg.message_text,
            "message_type": msg.message_type,
            "is_read": msg.is_read,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        })
    
    return result


@router.put("/messages/{message_id}/read", response_model=dict)
def mark_message_read(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Mark a message as read"""
    
    message = db.query(models.ChatMessage).filter(
        and_(
            models.ChatMessage.id == message_id,
            models.ChatMessage.recipient_id == current_user.id
        )
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.is_read = True
    message.read_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Message marked as read"}


# ============================================================================
# CHAT CHANNELS
# ============================================================================

@router.post("/channels", response_model=dict)
def create_channel(
    channel: schemas.ChatChannelCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a chat channel (department, project, etc.)"""
    
    db_channel = models.ChatChannel(
        company_id=current_user.company_id,
        channel_name=channel.channel_name,
        channel_type=channel.channel_type or "department",
        description=channel.description,
        created_by=current_user.id
    )
    
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    
    return {
        "id": db_channel.id,
        "channel_name": db_channel.channel_name,
        "message": "Channel created successfully"
    }


@router.get("/channels", response_model=List[dict])
def list_channels(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all chat channels"""
    
    channels = db.query(models.ChatChannel).filter(
        models.ChatChannel.company_id == current_user.company_id
    ).all()
    
    return [
        {
            "id": ch.id,
            "channel_name": ch.channel_name,
            "channel_type": ch.channel_type,
            "description": ch.description,
            "member_count": 0  # TODO: Implement member tracking
        }
        for ch in channels
    ]


# ============================================================================
# UNREAD COUNT
# ============================================================================

@router.get("/unread-count", response_model=dict)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get count of unread messages"""
    
    count = db.query(func.count(models.ChatMessage.id)).filter(
        and_(
            models.ChatMessage.recipient_id == current_user.id,
            models.ChatMessage.is_read == False
        )
    ).scalar()
    
    return {"unread_count": count or 0}


# ============================================================================
# WEBSOCKET FOR REAL-TIME CHAT
# ============================================================================

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat"""
    
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Broadcast message to recipient
            if "recipient_id" in message_data:
                await manager.send_personal_message(
                    json.dumps(message_data),
                    message_data["recipient_id"]
                )
            else:
                # Broadcast to all in company
                await manager.broadcast(json.dumps(message_data), message_data.get("company_id"))
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Subscriber, TelecomPlan
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/telecom", tags=["telecom"])

# Subscribers
@router.post("/subscribers")
async def create_subscriber(
    subscriber: schemas.SubscriberCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_subscriber = Subscriber(**subscriber.dict(), company_id=current_user.company_id)
    db.add(db_subscriber)
    db.commit()
    db.refresh(db_subscriber)
    return db_subscriber

@router.get("/subscribers")
async def get_subscribers(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Subscriber).filter(
        Subscriber.company_id == current_user.company_id
    ).all()

@router.get("/subscribers/{subscriber_id}")
async def get_subscriber(
    subscriber_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    subscriber = db.query(Subscriber).filter(
        Subscriber.id == subscriber_id,
        Subscriber.company_id == current_user.company_id
    ).first()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscriber

@router.put("/subscribers/{subscriber_id}")
async def update_subscriber(
    subscriber_id: str,
    subscriber_update: schemas.SubscriberCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    subscriber = db.query(Subscriber).filter(
        Subscriber.id == subscriber_id,
        Subscriber.company_id == current_user.company_id
    ).first()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    for key, value in subscriber_update.dict(exclude_unset=True).items():
        setattr(subscriber, key, value)
    
    db.commit()
    db.refresh(subscriber)
    return subscriber

@router.delete("/subscribers/{subscriber_id}")
async def delete_subscriber(
    subscriber_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    subscriber = db.query(Subscriber).filter(
        Subscriber.id == subscriber_id,
        Subscriber.company_id == current_user.company_id
    ).first()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    db.delete(subscriber)
    db.commit()
    return {"message": "Subscriber deleted successfully"}

# Telecom Plans
@router.post("/plans")
async def create_plan(
    plan: schemas.TelecomPlanCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_plan = TelecomPlan(**plan.dict(), company_id=current_user.company_id)
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

@router.get("/plans")
async def get_plans(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(TelecomPlan).filter(
        TelecomPlan.company_id == current_user.company_id
    ).all()

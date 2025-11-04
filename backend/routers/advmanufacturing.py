from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import AdvProductionOrder, AdvQualityControl
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/advmanufacturing", tags=["advmanufacturing"])

# Production Orders
@router.post("/production-orders")
async def create_production_order(
    order: schemas.ProductionOrderCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_order = AdvProductionOrder(**order.dict(), company_id=current_user.company_id)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@router.get("/production-orders")
async def get_production_orders(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(AdvProductionOrder).filter(
        AdvProductionOrder.company_id == current_user.company_id
    ).all()

@router.get("/production-orders/{order_id}")
async def get_production_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    order = db.query(AdvProductionOrder).filter(
        AdvProductionOrder.id == order_id,
        AdvProductionOrder.company_id == current_user.company_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")
    return order

@router.put("/production-orders/{order_id}")
async def update_production_order(
    order_id: str,
    order_update: schemas.ProductionOrderCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    order = db.query(AdvProductionOrder).filter(
        AdvProductionOrder.id == order_id,
        AdvProductionOrder.company_id == current_user.company_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")
    
    for key, value in order_update.dict(exclude_unset=True).items():
        setattr(order, key, value)
    
    db.commit()
    db.refresh(order)
    return order

@router.delete("/production-orders/{order_id}")
async def delete_production_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    order = db.query(AdvProductionOrder).filter(
        AdvProductionOrder.id == order_id,
        AdvProductionOrder.company_id == current_user.company_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")
    
    db.delete(order)
    db.commit()
    return {"message": "Production order deleted successfully"}

# Quality Control
@router.post("/quality-control")
async def create_quality_control(
    qc: schemas.QualityControlCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_qc = AdvQualityControl(**qc.dict(), company_id=current_user.company_id)
    db.add(db_qc)
    db.commit()
    db.refresh(db_qc)
    return db_qc

@router.get("/quality-control")
async def get_quality_controls(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(AdvQualityControl).filter(
        AdvQualityControl.company_id == current_user.company_id
    ).all()

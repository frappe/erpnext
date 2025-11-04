from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Meter, Consumption
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/energy", tags=["energy"])

# Meters
@router.post("/meters")
async def create_meter(
    meter: schemas.MeterCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_meter = Meter(**meter.dict(), company_id=current_user.company_id)
    db.add(db_meter)
    db.commit()
    db.refresh(db_meter)
    return db_meter

@router.get("/meters")
async def get_meters(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Meter).filter(
        Meter.company_id == current_user.company_id
    ).all()

@router.get("/meters/{meter_id}")
async def get_meter(
    meter_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    meter = db.query(Meter).filter(
        Meter.id == meter_id,
        Meter.company_id == current_user.company_id
    ).first()
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found")
    return meter

@router.put("/meters/{meter_id}")
async def update_meter(
    meter_id: str,
    meter_update: schemas.MeterCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    meter = db.query(Meter).filter(
        Meter.id == meter_id,
        Meter.company_id == current_user.company_id
    ).first()
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found")
    
    for key, value in meter_update.dict(exclude_unset=True).items():
        setattr(meter, key, value)
    
    db.commit()
    db.refresh(meter)
    return meter

@router.delete("/meters/{meter_id}")
async def delete_meter(
    meter_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    meter = db.query(Meter).filter(
        Meter.id == meter_id,
        Meter.company_id == current_user.company_id
    ).first()
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found")
    
    db.delete(meter)
    db.commit()
    return {"message": "Meter deleted successfully"}

# Consumption
@router.post("/consumption")
async def create_consumption(
    consumption: schemas.ConsumptionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_consumption = Consumption(**consumption.dict(), company_id=current_user.company_id)
    db.add(db_consumption)
    db.commit()
    db.refresh(db_consumption)
    return db_consumption

@router.get("/consumption")
async def get_consumptions(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Consumption).filter(
        Consumption.company_id == current_user.company_id
    ).all()

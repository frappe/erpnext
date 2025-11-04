from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Permit, PublicService
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/government", tags=["government"])

# Permits
@router.post("/permits")
async def create_permit(
    permit: schemas.PermitCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_permit = Permit(**permit.dict(), company_id=current_user.company_id)
    db.add(db_permit)
    db.commit()
    db.refresh(db_permit)
    return db_permit

@router.get("/permits")
async def get_permits(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Permit).filter(
        Permit.company_id == current_user.company_id
    ).all()

@router.get("/permits/{permit_id}")
async def get_permit(
    permit_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    permit = db.query(Permit).filter(
        Permit.id == permit_id,
        Permit.company_id == current_user.company_id
    ).first()
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")
    return permit

@router.put("/permits/{permit_id}")
async def update_permit(
    permit_id: str,
    permit_update: schemas.PermitCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    permit = db.query(Permit).filter(
        Permit.id == permit_id,
        Permit.company_id == current_user.company_id
    ).first()
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")
    
    for key, value in permit_update.dict(exclude_unset=True).items():
        setattr(permit, key, value)
    
    db.commit()
    db.refresh(permit)
    return permit

@router.delete("/permits/{permit_id}")
async def delete_permit(
    permit_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    permit = db.query(Permit).filter(
        Permit.id == permit_id,
        Permit.company_id == current_user.company_id
    ).first()
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")
    
    db.delete(permit)
    db.commit()
    return {"message": "Permit deleted successfully"}

# Public Services
@router.post("/services")
async def create_service(
    service: schemas.PublicServiceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_service = PublicService(**service.dict(), company_id=current_user.company_id)
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

@router.get("/services")
async def get_services(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(PublicService).filter(
        PublicService.company_id == current_user.company_id
    ).all()

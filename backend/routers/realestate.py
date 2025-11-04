from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import RealEstateProperty, Lease
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/realestate", tags=["realestate"])

# Properties
@router.post("/properties")
async def create_property(
    property: schemas.RealEstatePropertyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_property = RealEstateProperty(**property.dict(), company_id=current_user.company_id)
    db.add(db_property)
    db.commit()
    db.refresh(db_property)
    return db_property

@router.get("/properties")
async def get_properties(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(RealEstateProperty).filter(
        RealEstateProperty.company_id == current_user.company_id
    ).all()

@router.get("/properties/{property_id}")
async def get_property(
    property_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    property = db.query(RealEstateProperty).filter(
        RealEstateProperty.id == property_id,
        RealEstateProperty.company_id == current_user.company_id
    ).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    return property

@router.put("/properties/{property_id}")
async def update_property(
    property_id: str,
    property_update: schemas.RealEstatePropertyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    property = db.query(RealEstateProperty).filter(
        RealEstateProperty.id == property_id,
        RealEstateProperty.company_id == current_user.company_id
    ).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    for key, value in property_update.dict(exclude_unset=True).items():
        setattr(property, key, value)
    
    db.commit()
    db.refresh(property)
    return property

@router.delete("/properties/{property_id}")
async def delete_property(
    property_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    property = db.query(RealEstateProperty).filter(
        RealEstateProperty.id == property_id,
        RealEstateProperty.company_id == current_user.company_id
    ).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    
    db.delete(property)
    db.commit()
    return {"message": "Property deleted successfully"}

# Leases
@router.post("/leases")
async def create_lease(
    lease: schemas.LeaseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_lease = Lease(**lease.dict(), company_id=current_user.company_id)
    db.add(db_lease)
    db.commit()
    db.refresh(db_lease)
    return db_lease

@router.get("/leases")
async def get_leases(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Lease).filter(
        Lease.company_id == current_user.company_id
    ).all()

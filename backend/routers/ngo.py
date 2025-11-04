from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Donor, Grant
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/ngo", tags=["ngo"])

# Donors
@router.post("/donors")
async def create_donor(
    donor: schemas.DonorCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_donor = Donor(**donor.dict(), company_id=current_user.company_id)
    db.add(db_donor)
    db.commit()
    db.refresh(db_donor)
    return db_donor

@router.get("/donors")
async def get_donors(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Donor).filter(
        Donor.company_id == current_user.company_id
    ).all()

@router.get("/donors/{donor_id}")
async def get_donor(
    donor_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    donor = db.query(Donor).filter(
        Donor.id == donor_id,
        Donor.company_id == current_user.company_id
    ).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    return donor

@router.put("/donors/{donor_id}")
async def update_donor(
    donor_id: str,
    donor_update: schemas.DonorCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    donor = db.query(Donor).filter(
        Donor.id == donor_id,
        Donor.company_id == current_user.company_id
    ).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    
    for key, value in donor_update.dict(exclude_unset=True).items():
        setattr(donor, key, value)
    
    db.commit()
    db.refresh(donor)
    return donor

@router.delete("/donors/{donor_id}")
async def delete_donor(
    donor_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    donor = db.query(Donor).filter(
        Donor.id == donor_id,
        Donor.company_id == current_user.company_id
    ).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    
    db.delete(donor)
    db.commit()
    return {"message": "Donor deleted successfully"}

# Grants
@router.post("/grants")
async def create_grant(
    grant: schemas.GrantCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_grant = Grant(**grant.dict(), company_id=current_user.company_id)
    db.add(db_grant)
    db.commit()
    db.refresh(db_grant)
    return db_grant

@router.get("/grants")
async def get_grants(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Grant).filter(
        Grant.company_id == current_user.company_id
    ).all()

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import InsurancePolicy, Claim
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/insurance", tags=["insurance"])

# Policies
@router.post("/policies")
async def create_policy(
    policy: schemas.InsurancePolicyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_policy = InsurancePolicy(**policy.dict(), company_id=current_user.company_id)
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy

@router.get("/policies")
async def get_policies(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(InsurancePolicy).filter(
        InsurancePolicy.company_id == current_user.company_id
    ).all()

@router.get("/policies/{policy_id}")
async def get_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    policy = db.query(InsurancePolicy).filter(
        InsurancePolicy.id == policy_id,
        InsurancePolicy.company_id == current_user.company_id
    ).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@router.put("/policies/{policy_id}")
async def update_policy(
    policy_id: str,
    policy_update: schemas.InsurancePolicyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    policy = db.query(InsurancePolicy).filter(
        InsurancePolicy.id == policy_id,
        InsurancePolicy.company_id == current_user.company_id
    ).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    for key, value in policy_update.dict(exclude_unset=True).items():
        setattr(policy, key, value)
    
    db.commit()
    db.refresh(policy)
    return policy

@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    policy = db.query(InsurancePolicy).filter(
        InsurancePolicy.id == policy_id,
        InsurancePolicy.company_id == current_user.company_id
    ).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    db.delete(policy)
    db.commit()
    return {"message": "Policy deleted successfully"}

# Claims
@router.post("/claims")
async def create_claim(
    claim: schemas.ClaimCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_claim = Claim(**claim.dict(), company_id=current_user.company_id)
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    return db_claim

@router.get("/claims")
async def get_claims(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Claim).filter(
        Claim.company_id == current_user.company_id
    ).all()

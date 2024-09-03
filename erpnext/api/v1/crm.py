from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from Goldfish.config import get_db
from Goldfish.models.crm import Lead, Opportunity, OpportunityItem
from Goldfish.business_logic.crm import validate_lead, convert_lead_to_opportunity, validate_opportunity, update_opportunity_amount
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from Goldfish.utils.exceptions import ValidationError, NotFoundError
from Goldfish.auth.jwt import verify_token
from Goldfish.models.user import User

router = APIRouter()

# Lead API
class LeadCreate(BaseModel):
    lead_name: str
    company_name: str
    status: str
    email: str
    phone: str
    attachment_url: Optional[str] = None

class LeadUpdate(BaseModel):
    lead_name: Optional[str]
    company_name: Optional[str]
    status: Optional[str]
    email: Optional[str]
    phone: Optional[str]

@router.post("/leads/", response_model=LeadCreate)
async def create_lead(lead: LeadCreate, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    try:
        db_lead = Lead(**lead.dict())
        validate_lead(db, db_lead)
        db.add(db_lead)
        db.commit()
        db.refresh(db_lead)
        return db_lead
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/leads/{lead_id}")
def read_lead(lead_id: str, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    lead = db.query(Lead).filter(Lead.name == lead_id).first()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.put("/leads/{lead_id}")
def update_lead(lead_id: str, lead: LeadUpdate, db: Session = Depends(get_db), current_user: User = Depends(has_permission("Sales User"))):
    db_lead = db.query(Lead).filter(Lead.name == lead_id).first()
    if db_lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    for key, value in lead.dict(exclude_unset=True).items():
        setattr(db_lead, key, value)
    db.commit()
    db.refresh(db_lead)
    return db_lead

@router.delete("/leads/{lead_id}")
def delete_lead(lead_id: str, db: Session = Depends(get_db), current_user: User = Depends(has_permission("Sales Manager"))):
    db_lead = db.query(Lead).filter(Lead.name == lead_id).first()
    if db_lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(db_lead)
    db.commit()
    return {"message": "Lead deleted successfully"}

# Opportunity API
class OpportunityItemCreate(BaseModel):
    item_code: str
    qty: float

class OpportunityCreate(BaseModel):
    opportunity_from: str
    party_name: str
    status: str
    expected_closing: datetime
    items: List[OpportunityItemCreate]

class OpportunityUpdate(BaseModel):
    opportunity_from: Optional[str]
    party_name: Optional[str]
    status: Optional[str]
    expected_closing: Optional[datetime]

@router.post("/opportunities/", response_model=OpportunityCreate)
def create_opportunity(opportunity: OpportunityCreate, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    try:
        db_opportunity = Opportunity(
            opportunity_from=opportunity.opportunity_from,
            party_name=opportunity.party_name,
            status=opportunity.status,
            expected_closing=opportunity.expected_closing
        )
        db.add(db_opportunity)
        db.flush()

        for item in opportunity.items:
            db_item = OpportunityItem(
                parent=db_opportunity.name,
                item_code=item.item_code,
                qty=item.qty
            )
            db.add(db_item)

        validate_opportunity(db, db_opportunity)
        update_opportunity_amount(db, db_opportunity)
        db.commit()
        db.refresh(db_opportunity)
        return db_opportunity
    except (ValidationError, NotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/opportunities/{opportunity_id}")
def read_opportunity(opportunity_id: str, db: Session = Depends(get_db)):
    opportunity = db.query(Opportunity).filter(Opportunity.name == opportunity_id).first()
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity

@router.put("/opportunities/{opportunity_id}")
def update_opportunity(opportunity_id: str, opportunity: OpportunityUpdate, db: Session = Depends(get_db), current_user: User = Depends(has_permission("Sales User"))):
    db_opportunity = db.query(Opportunity).filter(Opportunity.name == opportunity_id).first()
    if db_opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    for key, value in opportunity.dict(exclude_unset=True).items():
        setattr(db_opportunity, key, value)
    db.commit()
    db.refresh(db_opportunity)
    return db_opportunity

@router.delete("/opportunities/{opportunity_id}")
def delete_opportunity(opportunity_id: str, db: Session = Depends(get_db), current_user: User = Depends(has_permission("Sales Manager"))):
    db_opportunity = db.query(Opportunity).filter(Opportunity.name == opportunity_id).first()
    if db_opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    db.delete(db_opportunity)
    db.commit()
    return {"message": "Opportunity deleted successfully"}
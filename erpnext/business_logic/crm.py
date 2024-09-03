from sqlalchemy.orm import Session
from Goldfish.models.crm import Lead, Opportunity, OpportunityItem
from Goldfish.models.item import Item
from datetime import datetime
from Goldfish.utils.exceptions import ValidationError, NotFoundError

def validate_lead(db: Session, lead: Lead):
    if not lead.email and not lead.phone:
        raise ValidationError("Either email or phone must be provided for a lead")
    
    # Check for duplicate leads
    existing_lead = db.query(Lead).filter(
        (Lead.email == lead.email) | (Lead.phone == lead.phone)
    ).first()
    if existing_lead:
        raise ValidationError(f"A lead with this email or phone already exists: {existing_lead.name}")

def convert_lead_to_opportunity(db: Session, lead_id: str) -> Opportunity:
    lead = db.query(Lead).filter(Lead.name == lead_id).first()
    if not lead:
        raise NotFoundError(f"Lead not found: {lead_id}")
    
    opportunity = Opportunity(
        opportunity_from="Lead",
        party_name=lead.company_name,
        status="Open",
        expected_closing=datetime.now().date()
    )
    db.add(opportunity)
    db.flush()
    
    lead.status = "Opportunity"
    db.commit()
    return opportunity

def validate_opportunity(db: Session, opportunity: Opportunity):
    if not opportunity.items:
        raise ValidationError("An opportunity must have at least one item")
    
    for item in opportunity.items:
        db_item = db.query(Item).filter(Item.item_code == item.item_code).first()
        if not db_item:
            raise NotFoundError(f"Item not found: {item.item_code}")
        
        if item.qty <= 0:
            raise ValidationError(f"Quantity must be greater than zero for item: {item.item_code}")

def update_opportunity_amount(db: Session, opportunity: Opportunity):
    total_amount = sum(item.qty * item.rate for item in opportunity.items)
    opportunity.total_amount = total_amount
    db.commit()
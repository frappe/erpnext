"""
Compliance & Statutory Obligations API Routes

Endpoints for:
- Statutory obligations management
- Compliance checklists
- Compliance dashboard
- Notification management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel

import models
from database import get_db
from auth import get_current_user
from services.compliance.statutory_compliance import StatutoryComplianceService

router = APIRouter(prefix="/api/compliance", tags=["Compliance"])


class StatutoryObligationCreate(BaseModel):
    obligation_type: str
    obligation_name: str
    period_start: date
    period_end: date
    due_date: date
    amount_due: Optional[float] = 0.0
    alert_days_before: Optional[int] = 5
    notes: Optional[str] = None


class StatutoryObligationUpdate(BaseModel):
    amount_due: Optional[float] = None
    amount_paid: Optional[float] = None
    status: Optional[str] = None
    confirmed_by_user: Optional[bool] = None
    payment_reference: Optional[str] = None
    payment_date: Optional[date] = None
    notes: Optional[str] = None


class ComplianceChecklistUpdate(BaseModel):
    is_completed: bool
    attachment_path: Optional[str] = None


@router.post("/obligations/generate-monthly/{year}/{month}")
def generate_monthly_obligations(
    year: int,
    month: int,
    enabled_types: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Generate statutory obligations for a specific month"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = StatutoryComplianceService(db)
    obligations = service.generate_monthly_obligations(
        company_id=current_user.company_id,
        year=year,
        month=month,
        enabled_obligations=enabled_types
    )
    
    return {
        "success": True,
        "count": len(obligations),
        "obligations": [
            {
                "id": o.id,
                "type": o.obligation_type,
                "name": o.obligation_name,
                "due_date": o.due_date,
                "status": o.status
            }
            for o in obligations
        ]
    }


@router.get("/obligations")
def list_obligations(
    status: Optional[str] = None,
    obligation_type: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all statutory obligations"""
    query = db.query(models.StatutoryObligation).filter(
        models.StatutoryObligation.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.StatutoryObligation.status == status)
    if obligation_type:
        query = query.filter(models.StatutoryObligation.obligation_type == obligation_type)
    if from_date:
        query = query.filter(models.StatutoryObligation.due_date >= from_date)
    if to_date:
        query = query.filter(models.StatutoryObligation.due_date <= to_date)
    
    obligations = query.order_by(models.StatutoryObligation.due_date).all()
    
    return {
        "success": True,
        "count": len(obligations),
        "obligations": obligations
    }


@router.get("/obligations/{obligation_id}")
def get_obligation(
    obligation_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get obligation details with compliance percentage"""
    obligation = db.query(models.StatutoryObligation).filter(
        models.StatutoryObligation.id == obligation_id,
        models.StatutoryObligation.company_id == current_user.company_id
    ).first()
    
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")
    
    # Get checklist
    checklist = db.query(models.ComplianceChecklist).filter(
        models.ComplianceChecklist.obligation_id == obligation_id
    ).order_by(models.ComplianceChecklist.sequence_order).all()
    
    # Calculate compliance percentage
    service = StatutoryComplianceService(db)
    compliance = service.calculate_compliance_percentage(obligation_id)
    
    return {
        "success": True,
        "obligation": obligation,
        "checklist": checklist,
        "compliance": compliance
    }


@router.put("/obligations/{obligation_id}")
def update_obligation(
    obligation_id: str,
    data: StatutoryObligationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update obligation"""
    obligation = db.query(models.StatutoryObligation).filter(
        models.StatutoryObligation.id == obligation_id,
        models.StatutoryObligation.company_id == current_user.company_id
    ).first()
    
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")
    
    # Update fields
    for field, value in data.dict(exclude_unset=True).items():
        setattr(obligation, field, value)
    
    # If confirming, set confirmation details
    if data.confirmed_by_user:
        obligation.confirmed_at = datetime.now()
        obligation.confirmed_by = current_user.id
    
    # Update status based on payment
    if data.amount_paid and data.amount_paid >= obligation.amount_due:
        obligation.status = "paid"
    
    db.commit()
    db.refresh(obligation)
    
    return {"success": True, "obligation": obligation}


@router.put("/checklist/{checklist_id}")
def update_checklist_item(
    checklist_id: str,
    data: ComplianceChecklistUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update checklist item completion"""
    item = db.query(models.ComplianceChecklist).filter(
        models.ComplianceChecklist.id == checklist_id,
        models.ComplianceChecklist.company_id == current_user.company_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    
    item.is_completed = data.is_completed
    if data.is_completed:
        item.completed_at = datetime.now()
        item.completed_by = current_user.id
    
    if data.attachment_path:
        item.attachment_path = data.attachment_path
    
    db.commit()
    
    # Update obligation compliance status
    obligation = db.query(models.StatutoryObligation).filter(
        models.StatutoryObligation.id == item.obligation_id
    ).first()
    
    service = StatutoryComplianceService(db)
    compliance = service.calculate_compliance_percentage(item.obligation_id)
    
    if compliance["completion_percentage"] == 100:
        obligation.compliance_status = "completed"
    elif compliance["completion_percentage"] > 0:
        obligation.compliance_status = "in_progress"
    
    db.commit()
    
    return {"success": True, "item": item, "compliance": compliance}


@router.get("/dashboard")
def compliance_dashboard(
    period: str = "current_month",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get compliance dashboard with percentage tracking"""
    service = StatutoryComplianceService(db)
    dashboard = service.get_compliance_dashboard(
        company_id=current_user.company_id,
        period=period
    )
    
    return {"success": True, "dashboard": dashboard}


@router.post("/check-alerts")
def check_and_send_alerts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Check for upcoming obligations and send alerts"""
    service = StatutoryComplianceService(db)
    notifications = service.check_and_send_alerts(current_user.company_id)
    
    return {
        "success": True,
        "alerts_created": len(notifications),
        "notifications": notifications
    }


@router.get("/notifications")
def get_notifications(
    is_read: Optional[bool] = None,
    notification_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get user notifications"""
    query = db.query(models.Notification).filter(
        models.Notification.company_id == current_user.company_id
    )
    
    if current_user.role != "admin":
        query = query.filter(models.Notification.user_id == current_user.id)
    
    if is_read is not None:
        query = query.filter(models.Notification.is_read == is_read)
    if notification_type:
        query = query.filter(models.Notification.notification_type == notification_type)
    
    notifications = query.order_by(
        models.Notification.created_at.desc()
    ).limit(limit).all()
    
    return {
        "success": True,
        "count": len(notifications),
        "notifications": notifications
    }


@router.get("/notifications/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get count of unread notifications"""
    count = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()
    
    return {"success": True, "unread_count": count}


@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Mark notification as read"""
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    notification.read_at = datetime.now()
    
    db.commit()
    
    return {"success": True, "notification": notification}

"""
Super Admin API Routes

Endpoints for platform-wide management:
- Tenant management (list, create, suspend, upgrade)
- Subscription plan management  
- Platform analytics and monitoring
- Support ticket management
- System settings
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import date, datetime, timedelta
from pydantic import BaseModel

import models
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/super-admin", tags=["Super Admin"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SubscriptionPlanCreate(BaseModel):
    plan_code: str
    plan_name: str
    description: Optional[str] = None
    price_monthly: float = 0.0
    price_annual: float = 0.0
    currency: str = "ZMW"
    max_users: int = 5
    max_employees: int = 50
    max_storage_gb: int = 10
    max_api_calls_per_month: int = 10000
    max_branches: int = 1
    modules_included: List[str] = []
    features_included: List[str] = []
    trial_days: int = 7
    is_active: bool = True
    is_public: bool = True


class TenantUpdate(BaseModel):
    subscription_plan: Optional[str] = None
    subscription_status: Optional[str] = None
    is_active: Optional[bool] = None


class SupportTicketCreate(BaseModel):
    company_id: str
    subject: str
    description: str
    category: Optional[str] = "technical"
    priority: Optional[str] = "medium"


class SupportTicketUpdate(BaseModel):
    assigned_to: Optional[str] = None
    status: Optional[str] = None
    resolution: Optional[str] = None


# ============================================================================
# MIDDLEWARE
# ============================================================================

def get_super_admin_user(current_user: models.User = Depends(get_current_user)):
    """Verify user is a super admin"""
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="Super admin access required"
        )
    return current_user


# ============================================================================
# TENANT MANAGEMENT
# ============================================================================

@router.get("/tenants")
def list_tenants(
    status: Optional[str] = Query(None),
    subscription_plan: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """List all tenants with filtering and pagination"""
    
    query = db.query(models.Company)
    
    # Filters
    if status:
        query = query.filter(models.Company.subscription_status == status)
    if subscription_plan:
        query = query.filter(models.Company.subscription_plan == subscription_plan)
    if search:
        search_filter = or_(
            models.Company.name.ilike(f"%{search}%"),
            models.Company.email.ilike(f"%{search}%"),
            models.Company.tax_id.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    total = query.count()
    tenants = query.offset(skip).limit(limit).all()
    
    # Enrich with stats
    tenant_list = []
    for tenant in tenants:
        user_count = db.query(models.User).filter(models.User.company_id == tenant.id).count()
        employee_count = db.query(models.Employee).filter(models.Employee.company_id == tenant.id).count()
        
        tenant_data = {
            "id": tenant.id,
            "name": tenant.name,
            "email": tenant.email,
            "tax_id": tenant.tax_id,
            "subscription_plan": tenant.subscription_plan,
            "subscription_status": tenant.subscription_status,
            "trial_ends_at": tenant.trial_ends_at,
            "subscription_ends_at": tenant.subscription_ends_at,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at,
            "user_count": user_count,
            "employee_count": employee_count
        }
        tenant_list.append(tenant_data)
    
    return {
        "tenants": tenant_list,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/tenants/{tenant_id}")
def get_tenant_details(
    tenant_id: str,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """Get detailed information about a specific tenant"""
    
    tenant = db.query(models.Company).filter(models.Company.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get tenant stats
    user_count = db.query(models.User).filter(models.User.company_id == tenant_id).count()
    employee_count = db.query(models.Employee).filter(models.Employee.company_id == tenant_id).count()
    
    # Get API usage for current month
    current_month = datetime.utcnow().strftime("%Y-%m")
    api_calls = db.query(func.count(models.APIUsageLog.id)).filter(
        models.APIUsageLog.company_id == tenant_id,
        models.APIUsageLog.year_month == current_month
    ).scalar()
    
    # Get open support tickets
    open_tickets = db.query(func.count(models.SupportTicket.id)).filter(
        models.SupportTicket.company_id == tenant_id,
        models.SupportTicket.status.in_(["open", "in_progress"])
    ).scalar()
    
    # Serialize tenant to dict
    tenant_data = {
        "id": tenant.id,
        "name": tenant.name,
        "email": tenant.email,
        "phone": tenant.phone,
        "address": tenant.address,
        "city": tenant.city,
        "country": tenant.country,
        "tax_id": tenant.tax_id,
        "currency": tenant.currency,
        "fiscal_year_end": tenant.fiscal_year_end,
        "subscription_plan": tenant.subscription_plan,
        "subscription_status": tenant.subscription_status,
        "trial_ends_at": tenant.trial_ends_at,
        "subscription_ends_at": tenant.subscription_ends_at,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at
    }
    
    return {
        "tenant": tenant_data,
        "stats": {
            "user_count": user_count,
            "employee_count": employee_count,
            "api_calls_this_month": api_calls or 0,
            "open_support_tickets": open_tickets or 0
        }
    }


@router.patch("/tenants/{tenant_id}")
def update_tenant(
    tenant_id: str,
    data: TenantUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """Update tenant details (subscription, status, etc.)"""
    
    tenant = db.query(models.Company).filter(models.Company.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if data.subscription_plan is not None:
        tenant.subscription_plan = data.subscription_plan
    if data.subscription_status is not None:
        tenant.subscription_status = data.subscription_status
    if data.is_active is not None:
        tenant.is_active = data.is_active
    
    db.commit()
    db.refresh(tenant)
    
    # Serialize tenant to dict
    tenant_data = {
        "id": tenant.id,
        "name": tenant.name,
        "email": tenant.email,
        "subscription_plan": tenant.subscription_plan,
        "subscription_status": tenant.subscription_status,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at
    }
    
    return {"success": True, "tenant": tenant_data}


@router.post("/tenants/{tenant_id}/suspend")
def suspend_tenant(
    tenant_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """Suspend a tenant (disable access)"""
    
    tenant = db.query(models.Company).filter(models.Company.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant.is_active = False
    tenant.subscription_status = "suspended"
    
    db.commit()
    
    return {"success": True, "message": f"Tenant {tenant.name} has been suspended"}


@router.post("/tenants/{tenant_id}/activate")
def activate_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """Activate a suspended tenant"""
    
    tenant = db.query(models.Company).filter(models.Company.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant.is_active = True
    tenant.subscription_status = "active"
    
    db.commit()
    
    return {"success": True, "message": f"Tenant {tenant.name} has been activated"}


# ============================================================================
# SUBSCRIPTION PLAN MANAGEMENT
# ============================================================================

@router.get("/subscription-plans")
def list_subscription_plans(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """List all subscription plans"""
    
    plans = db.query(models.SubscriptionPlan).order_by(models.SubscriptionPlan.sort_order).all()
    
    # Add tenant count for each plan
    plan_list = []
    for plan in plans:
        tenant_count = db.query(func.count(models.Company.id)).filter(
            models.Company.subscription_plan == plan.plan_code
        ).scalar()
        
        plan_data = {
            **plan.__dict__,
            "tenant_count": tenant_count or 0
        }
        plan_data.pop('_sa_instance_state', None)
        plan_list.append(plan_data)
    
    return {"plans": plan_list}


@router.post("/subscription-plans")
def create_subscription_plan(
    data: SubscriptionPlanCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """Create a new subscription plan"""
    
    # Check if plan code already exists
    existing = db.query(models.SubscriptionPlan).filter(
        models.SubscriptionPlan.plan_code == data.plan_code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Plan code already exists")
    
    plan = models.SubscriptionPlan(**data.dict())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    # Serialize plan to dict
    plan_data = {
        "id": plan.id,
        "plan_code": plan.plan_code,
        "plan_name": plan.plan_name,
        "description": plan.description,
        "price_monthly": plan.price_monthly,
        "price_annual": plan.price_annual,
        "currency": plan.currency,
        "max_users": plan.max_users,
        "max_employees": plan.max_employees,
        "max_storage_gb": plan.max_storage_gb,
        "max_api_calls_per_month": plan.max_api_calls_per_month,
        "max_branches": plan.max_branches,
        "is_active": plan.is_active,
        "created_at": plan.created_at
    }
    
    return {"success": True, "plan": plan_data}


@router.patch("/subscription-plans/{plan_id}")
def update_subscription_plan(
    plan_id: str,
    data: SubscriptionPlanCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """Update a subscription plan"""
    
    plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    for key, value in data.dict().items():
        setattr(plan, key, value)
    
    db.commit()
    db.refresh(plan)
    
    # Serialize plan to dict
    plan_data = {
        "id": plan.id,
        "plan_code": plan.plan_code,
        "plan_name": plan.plan_name,
        "description": plan.description,
        "price_monthly": plan.price_monthly,
        "price_annual": plan.price_annual,
        "currency": plan.currency,
        "max_users": plan.max_users,
        "max_employees": plan.max_employees,
        "max_storage_gb": plan.max_storage_gb,
        "max_api_calls_per_month": plan.max_api_calls_per_month,
        "max_branches": plan.max_branches,
        "is_active": plan.is_active,
        "created_at": plan.created_at
    }
    
    return {"success": True, "plan": plan_data}


# ============================================================================
# PLATFORM ANALYTICS
# ============================================================================

@router.get("/analytics/dashboard")
def get_platform_analytics(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """Get platform-wide analytics for dashboard"""
    
    # Tenant stats
    total_tenants = db.query(func.count(models.Company.id)).scalar()
    active_tenants = db.query(func.count(models.Company.id)).filter(
        models.Company.is_active == True
    ).scalar()
    trial_tenants = db.query(func.count(models.Company.id)).filter(
        models.Company.subscription_plan == "trial"
    ).scalar()
    
    # Subscription breakdown
    subscription_breakdown = db.query(
        models.Company.subscription_plan,
        func.count(models.Company.id).label('count')
    ).group_by(models.Company.subscription_plan).all()
    
    # Revenue (mock calculation - would integrate with payment system)
    monthly_revenue = 0.0  # TODO: Calculate from subscription_payments table
    
    # Growth stats - tenants created this month
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_tenants_this_month = db.query(func.count(models.Company.id)).filter(
        models.Company.created_at >= start_of_month
    ).scalar()
    
    # Support tickets
    open_tickets = db.query(func.count(models.SupportTicket.id)).filter(
        models.SupportTicket.status.in_(["open", "in_progress"])
    ).scalar()
    
    # System logs - recent errors
    recent_errors = db.query(func.count(models.SystemLog.id)).filter(
        models.SystemLog.log_level.in_(["ERROR", "CRITICAL"]),
        models.SystemLog.timestamp >= datetime.utcnow() - timedelta(hours=24)
    ).scalar()
    
    return {
        "tenant_stats": {
            "total": total_tenants or 0,
            "active": active_tenants or 0,
            "trial": trial_tenants or 0,
            "new_this_month": new_tenants_this_month or 0
        },
        "subscription_breakdown": [
            {"plan": row[0], "count": row[1]}
            for row in subscription_breakdown
        ],
        "revenue": {
            "monthly": monthly_revenue,
            "currency": "ZMW"
        },
        "support": {
            "open_tickets": open_tickets or 0
        },
        "system_health": {
            "errors_24h": recent_errors or 0
        }
    }


@router.get("/analytics/tenants")
def get_tenant_analytics(
    period: str = Query("30d", regex="^(7d|30d|90d|365d)$"),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """Get tenant growth analytics"""
    
    # Calculate period
    days = int(period.replace('d', ''))
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Tenant creation by day
    tenant_growth = db.query(
        func.date(models.Company.created_at).label('date'),
        func.count(models.Company.id).label('count')
    ).filter(
        models.Company.created_at >= start_date
    ).group_by(
        func.date(models.Company.created_at)
    ).order_by('date').all()
    
    return {
        "period": period,
        "growth": [
            {"date": str(row[0]), "count": row[1]}
            for row in tenant_growth
        ]
    }


# ============================================================================
# SUPPORT TICKET MANAGEMENT
# ============================================================================

@router.get("/support/tickets")
def list_support_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """List all support tickets"""
    
    query = db.query(models.SupportTicket)
    
    if status:
        query = query.filter(models.SupportTicket.status == status)
    if priority:
        query = query.filter(models.SupportTicket.priority == priority)
    if category:
        query = query.filter(models.SupportTicket.category == category)
    
    total = query.count()
    tickets = query.order_by(models.SupportTicket.created_at.desc()).offset(skip).limit(limit).all()
    
    # Serialize tickets to list of dicts
    ticket_list = [
        {
            "id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "company_id": ticket.company_id,
            "subject": ticket.subject,
            "description": ticket.description,
            "category": ticket.category,
            "priority": ticket.priority,
            "status": ticket.status,
            "created_by": ticket.created_by,
            "assigned_to": ticket.assigned_to,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
            "resolved_at": ticket.resolved_at
        }
        for ticket in tickets
    ]
    
    return {
        "tickets": ticket_list,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/support/tickets")
def create_support_ticket(
    data: SupportTicketCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """Create a new support ticket"""
    
    # Generate ticket number
    ticket_count = db.query(func.count(models.SupportTicket.id)).scalar()
    ticket_number = f"TICKET-{(ticket_count or 0) + 1:06d}"
    
    ticket = models.SupportTicket(
        ticket_number=ticket_number,
        company_id=data.company_id,
        created_by=admin.id,
        subject=data.subject,
        description=data.description,
        category=data.category,
        priority=data.priority
    )
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    # Serialize ticket to dict
    ticket_data = {
        "id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "company_id": ticket.company_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "created_by": ticket.created_by,
        "created_at": ticket.created_at
    }
    
    return {"success": True, "ticket": ticket_data}


@router.patch("/support/tickets/{ticket_id}")
def update_support_ticket(
    ticket_id: str,
    data: SupportTicketUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    """Update a support ticket"""
    
    ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if data.assigned_to is not None:
        ticket.assigned_to = data.assigned_to
        ticket.assigned_at = datetime.utcnow()
    
    if data.status is not None:
        ticket.status = data.status
        if data.status in ["resolved", "closed"]:
            ticket.resolved_at = datetime.utcnow()
            ticket.resolved_by = admin.id
    
    if data.resolution is not None:
        ticket.resolution = data.resolution
    
    ticket.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ticket)
    
    # Serialize ticket to dict
    ticket_data = {
        "id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "company_id": ticket.company_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_to": ticket.assigned_to,
        "resolution": ticket.resolution,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "resolved_at": ticket.resolved_at
    }
    
    return {"success": True, "ticket": ticket_data}

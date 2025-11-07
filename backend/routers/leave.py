"""
Leave Management API Routes

Endpoints for:
- Leave type configuration
- Leave balance tracking
- Leave request submission
- Leave approval workflow
- Leave reports
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel

import models
from database import get_db
from auth import get_current_user
from services.hr.leave_service import LeaveService

router = APIRouter(prefix="/api/leave", tags=["Leave Management"])


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class LeaveTypeCreate(BaseModel):
    code: str
    name: str
    annual_allocation: float
    is_paid: bool = True
    requires_approval: bool = True


class LeaveRequestCreate(BaseModel):
    employee_id: str
    leave_type_id: str
    start_date: date
    end_date: date
    reason: str
    days_requested: Optional[float] = None


class LeaveApproval(BaseModel):
    comments: Optional[str] = None


# ============================================================================
# LEAVE TYPE ENDPOINTS
# ============================================================================

@router.post("/types")
def create_leave_type(
    data: LeaveTypeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new leave type"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Check for duplicate code
    existing = db.query(models.LeaveType).filter(
        models.LeaveType.company_id == current_user.company_id,
        models.LeaveType.code == data.code
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Leave type code already exists")
    
    leave_type = models.LeaveType(
        company_id=current_user.company_id,
        code=data.code,
        name=data.name,
        annual_allocation=data.annual_allocation,
        is_paid=data.is_paid,
        requires_approval=data.requires_approval
    )
    
    db.add(leave_type)
    db.commit()
    db.refresh(leave_type)
    
    return {
        "success": True,
        "message": "Leave type created successfully",
        "leave_type": {
            "id": leave_type.id,
            "code": leave_type.code,
            "name": leave_type.name,
            "annual_allocation": leave_type.annual_allocation,
            "is_paid": leave_type.is_paid,
            "requires_approval": leave_type.requires_approval
        }
    }


@router.get("/types")
def list_leave_types(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all leave types"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    leave_types = db.query(models.LeaveType).filter(
        models.LeaveType.company_id == current_user.company_id
    ).all()
    
    return {
        "success": True,
        "leave_types": [
            {
                "id": lt.id,
                "code": lt.code,
                "name": lt.name,
                "annual_allocation": lt.annual_allocation,
                "is_paid": lt.is_paid,
                "requires_approval": lt.requires_approval
            }
            for lt in leave_types
        ],
        "count": len(leave_types)
    }


# ============================================================================
# LEAVE BALANCE ENDPOINTS
# ============================================================================

@router.post("/balances/initialize/{employee_id}")
def initialize_leave_balances(
    employee_id: str,
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Initialize leave balances for an employee"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LeaveService(db)
    
    try:
        balances = service.initialize_employee_leave_balances(
            company_id=current_user.company_id,
            employee_id=employee_id,
            year=year
        )
        
        return {
            "success": True,
            "message": f"Leave balances initialized for {year}",
            "balances": balances
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balances/{employee_id}")
def get_leave_balances(
    employee_id: str,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get leave balances for an employee"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    if year is None:
        year = datetime.now().year
    
    service = LeaveService(db)
    balances = service.get_all_leave_balances(
        company_id=current_user.company_id,
        employee_id=employee_id,
        year=year
    )
    
    return {
        "success": True,
        "employee_id": employee_id,
        "year": year,
        "balances": balances
    }


# ============================================================================
# LEAVE REQUEST ENDPOINTS
# ============================================================================

@router.post("/requests")
def submit_leave_request(
    data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Submit a leave request"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LeaveService(db)
    
    try:
        result = service.submit_leave_request(
            company_id=current_user.company_id,
            employee_id=data.employee_id,
            leave_type_id=data.leave_type_id,
            start_date=data.start_date,
            end_date=data.end_date,
            reason=data.reason,
            submitted_by=current_user.id,
            days_requested=data.days_requested
        )
        
        return {
            "success": True,
            "message": "Leave request submitted successfully",
            "request": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/requests")
def list_leave_requests(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List leave requests with filters"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LeaveService(db)
    requests = service.get_leave_requests(
        company_id=current_user.company_id,
        employee_id=employee_id,
        status=status,
        start_date=start_date,
        end_date=end_date
    )
    
    return {
        "success": True,
        "requests": requests,
        "count": len(requests)
    }


@router.get("/requests/{request_id}")
def get_leave_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a specific leave request"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    request = db.query(models.LeaveApplication).filter(
        models.LeaveApplication.id == request_id,
        models.LeaveApplication.company_id == current_user.company_id
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    employee = db.query(models.Employee).get(request.employee_id)
    leave_type = db.query(models.LeaveType).get(request.leave_type_id)
    
    return {
        "success": True,
        "request": {
            "id": request.id,
            "employee_id": request.employee_id,
            "employee_name": f"{employee.first_name} {employee.last_name}" if employee else "Unknown",
            "leave_type_name": leave_type.name if leave_type else "Unknown",
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "days_requested": request.days_requested,
            "reason": request.reason,
            "status": request.status,
            "submitted_at": request.submitted_at.isoformat() if request.submitted_at else None,
            "approved_by": request.approved_by,
            "approved_at": request.approved_at.isoformat() if request.approved_at else None,
            "approver_comments": request.approver_comments
        }
    }


# ============================================================================
# LEAVE APPROVAL ENDPOINTS
# ============================================================================

@router.post("/requests/{request_id}/approve")
def approve_leave_request(
    request_id: str,
    data: LeaveApproval,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Approve a leave request"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LeaveService(db)
    
    try:
        result = service.approve_leave_request(
            company_id=current_user.company_id,
            leave_request_id=request_id,
            approved_by=current_user.id,
            comments=data.comments
        )
        
        return {
            "success": True,
            "message": "Leave request approved",
            "request": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/requests/{request_id}/reject")
def reject_leave_request(
    request_id: str,
    data: LeaveApproval,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Reject a leave request"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    if not data.comments:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    service = LeaveService(db)
    
    try:
        result = service.reject_leave_request(
            company_id=current_user.company_id,
            leave_request_id=request_id,
            rejected_by=current_user.id,
            rejection_reason=data.comments
        )
        
        return {
            "success": True,
            "message": "Leave request rejected",
            "request": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SELF-SERVICE ENDPOINTS
# ============================================================================

@router.post("/my-requests")
def submit_my_leave_request(
    data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Submit leave request for logged-in employee"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Find employee record for current user
    employee = db.query(models.Employee).filter(
        models.Employee.company_id == current_user.company_id,
        models.Employee.email == current_user.email
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee record not found for current user"
        )
    
    # Override employee_id with current employee
    data.employee_id = employee.id
    
    return submit_leave_request(data, db, current_user)


@router.get("/my-requests")
def get_my_leave_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get leave requests for logged-in employee"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Find employee record for current user
    employee = db.query(models.Employee).filter(
        models.Employee.company_id == current_user.company_id,
        models.Employee.email == current_user.email
    ).first()
    
    if not employee:
        return {
            "success": True,
            "requests": [],
            "count": 0
        }
    
    return list_leave_requests(
        employee_id=employee.id,
        status=status,
        db=db,
        current_user=current_user
    )


@router.get("/my-balances")
def get_my_leave_balances(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get leave balances for logged-in employee"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Find employee record for current user
    employee = db.query(models.Employee).filter(
        models.Employee.company_id == current_user.company_id,
        models.Employee.email == current_user.email
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee record not found for current user"
        )
    
    return get_leave_balances(
        employee_id=employee.id,
        year=year,
        db=db,
        current_user=current_user
    )

"""
Payroll Run API Routes

Endpoints for batch payroll processing:
- Create payroll runs
- Process employees in batch
- Preview payslips
- Validate and approve payroll
- Export payroll data
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel

import models
from database import get_db
from auth import get_current_user
from services.payroll.payroll_run_service import PayrollRunService

router = APIRouter(prefix="/api/payroll-runs", tags=["Payroll Runs"])


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class PayrollRunCreate(BaseModel):
    period_start: date
    period_end: date
    payment_date: date
    payrun_name: Optional[str] = None


class PayrollRunProcess(BaseModel):
    employee_ids: Optional[List[str]] = None  # If None, process all active employees


# ============================================================================
# PAYROLL RUN CREATION
# ============================================================================

@router.post("")
def create_payroll_run(
    data: PayrollRunCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new payroll run (period)"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = PayrollRunService(db)
    
    try:
        result = service.create_payroll_run(
            company_id=current_user.company_id,
            period_start=data.period_start,
            period_end=data.period_end,
            payment_date=data.payment_date,
            payrun_name=data.payrun_name,
            created_by=current_user.id
        )
        
        return {
            "success": True,
            "message": "Payroll run created successfully",
            "payroll_run": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def list_payroll_runs(
    status: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all payroll runs"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = PayrollRunService(db)
    
    try:
        runs = service.list_payroll_runs(
            company_id=current_user.company_id,
            status=status,
            year=year
        )
        
        return {
            "success": True,
            "payroll_runs": runs,
            "count": len(runs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{payrun_id}")
def get_payroll_run(
    payrun_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get payroll run details with payslips"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = PayrollRunService(db)
    
    try:
        result = service.get_payroll_run(
            company_id=current_user.company_id,
            payrun_id=payrun_id
        )
        
        return {
            "success": True,
            "payroll_run": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PAYROLL PROCESSING
# ============================================================================

@router.post("/{payrun_id}/process")
def process_payroll_run(
    payrun_id: str,
    data: PayrollRunProcess,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Process payroll for all employees (or selected employees)"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = PayrollRunService(db)
    
    try:
        result = service.process_payroll_run(
            company_id=current_user.company_id,
            payrun_id=payrun_id,
            employee_ids=data.employee_ids
        )
        
        return {
            "success": True,
            "message": f"Processed {result['processed']} employees",
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{payrun_id}/payslips")
def get_payroll_payslips(
    payrun_id: str,
    employee_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get payslips for a payroll run"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = PayrollRunService(db)
    
    try:
        payslips = service.get_payslips(
            company_id=current_user.company_id,
            payrun_id=payrun_id,
            employee_id=employee_id
        )
        
        return {
            "success": True,
            "payslips": payslips,
            "count": len(payslips)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PAYROLL VALIDATION & APPROVAL
# ============================================================================

@router.post("/{payrun_id}/validate")
def validate_payroll_run(
    payrun_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Validate payroll run before approval"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = PayrollRunService(db)
    
    try:
        result = service.validate_payroll_run(
            company_id=current_user.company_id,
            payrun_id=payrun_id,
            validated_by=current_user.id
        )
        
        if result["success"]:
            message = "Payroll validated successfully"
        else:
            message = f"Validation failed with {len(result['validation_errors'])} errors"
        
        return {
            **result,
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{payrun_id}/approve")
def approve_payroll_run(
    payrun_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Approve and finalize payroll run"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = PayrollRunService(db)
    
    try:
        result = service.approve_payroll_run(
            company_id=current_user.company_id,
            payrun_id=payrun_id,
            approved_by=current_user.id
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{payrun_id}")
def delete_payroll_run(
    payrun_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a draft payroll run"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Get payroll run
    payrun = db.query(models.Payrun).filter(
        models.Payrun.id == payrun_id,
        models.Payrun.company_id == current_user.company_id
    ).first()
    
    if not payrun:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    if payrun.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete payroll with status: {payrun.status}"
        )
    
    # Delete payslips and payrun
    db.query(models.Payslip).filter(
        models.Payslip.payrun_id == payrun_id
    ).delete()
    
    db.delete(payrun)
    db.commit()
    
    return {
        "success": True,
        "message": "Payroll run deleted successfully"
    }


# ============================================================================
# PREVIEW & SUMMARY
# ============================================================================

@router.get("/{payrun_id}/summary")
def get_payroll_summary(
    payrun_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get payroll run summary with totals"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    payrun = db.query(models.Payrun).filter(
        models.Payrun.id == payrun_id,
        models.Payrun.company_id == current_user.company_id
    ).first()
    
    if not payrun:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    # Get payslip count
    from sqlalchemy import func
    payslip_count = db.query(func.count(models.Payslip.id)).filter(
        models.Payslip.payrun_id == payrun_id
    ).scalar()
    
    # Get department breakdown
    department_totals = db.query(
        models.Payslip.department_name,
        func.count(models.Payslip.id).label("count"),
        func.sum(models.Payslip.total_earnings).label("total_earnings"),
        func.sum(models.Payslip.total_deductions).label("total_deductions"),
        func.sum(models.Payslip.net_pay).label("total_net")
    ).filter(
        models.Payslip.payrun_id == payrun_id
    ).group_by(
        models.Payslip.department_name
    ).all()
    
    return {
        "success": True,
        "summary": {
            "payrun_id": payrun.id,
            "payrun_number": payrun.payrun_number,
            "payrun_name": payrun.payrun_name,
            "period": {
                "start": payrun.period_start.isoformat(),
                "end": payrun.period_end.isoformat(),
                "payment_date": payrun.payment_date.isoformat()
            },
            "status": payrun.status,
            "employee_count": payslip_count,
            "totals": {
                "gross": payrun.total_gross,
                "deductions": payrun.total_deductions,
                "net": payrun.total_net,
                "employer_cost": payrun.total_employer_cost
            },
            "statutory": {
                "paye": payrun.total_paye,
                "napsa_employee": payrun.total_napsa_employee,
                "napsa_employer": payrun.total_napsa_employer,
                "nhima_employee": payrun.total_nhima_employee,
                "nhima_employer": payrun.total_nhima_employer
            },
            "department_breakdown": [
                {
                    "department": dept[0] or "Unassigned",
                    "employee_count": dept[1],
                    "total_earnings": float(dept[2] or 0),
                    "total_deductions": float(dept[3] or 0),
                    "total_net": float(dept[4] or 0)
                }
                for dept in department_totals
            ],
            "validation_errors": payrun.validation_errors
        }
    }

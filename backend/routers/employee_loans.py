"""
Employee Loans & Advances API Router

Endpoints for loan management, approval, disbursement, and tracking
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel

import models
from database import get_db
from auth import get_current_user
from services.hr.loan_service import LoanService

router = APIRouter(prefix="/api/employee-loans", tags=["Employee Loans"])


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class LoanCreateRequest(BaseModel):
    employee_id: str
    loan_type: str  # salary_advance, emergency_loan, housing_loan, etc.
    principal_amount: float
    interest_rate: float = 0.0
    repayment_months: int
    repayment_start_date: date
    loan_purpose: Optional[str] = None
    notes: Optional[str] = None


class LoanApprovalRequest(BaseModel):
    approval_notes: Optional[str] = None


class LoanRejectionRequest(BaseModel):
    rejection_reason: str


class LoanDisbursementRequest(BaseModel):
    disbursement_method: str  # bank_transfer, cash, offset_against_salary
    disbursement_reference: Optional[str] = None


class LoanPaymentRequest(BaseModel):
    payment_amount: float
    payment_date: date
    payment_method: str = "manual_payment"
    reference_number: Optional[str] = None
    notes: Optional[str] = None


# ============================================================================
# LOAN CREATION & MANAGEMENT
# ============================================================================

@router.post("")
def create_loan(
    data: LoanCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create new employee loan"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LoanService(db)
    
    try:
        loan = service.create_loan(
            company_id=current_user.company_id,
            employee_id=data.employee_id,
            loan_type=data.loan_type,
            principal_amount=data.principal_amount,
            interest_rate=data.interest_rate,
            repayment_months=data.repayment_months,
            repayment_start_date=data.repayment_start_date,
            loan_purpose=data.loan_purpose,
            created_by=current_user.id,
            notes=data.notes
        )
        
        return {
            "success": True,
            "message": "Loan created successfully",
            "loan": loan
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def get_company_loans(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all loans for company with optional filters"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LoanService(db)
    
    try:
        loans = service.get_company_loans(
            company_id=current_user.company_id,
            status=status,
            employee_id=employee_id
        )
        
        return {
            "success": True,
            "count": len(loans),
            "loans": loans
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{loan_id}")
def get_loan_details(
    loan_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get detailed loan information including payment history"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LoanService(db)
    
    try:
        details = service.get_loan_details(
            company_id=current_user.company_id,
            loan_id=loan_id
        )
        
        return {
            "success": True,
            **details
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employee/{employee_id}/active")
def get_employee_active_loans(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all active loans for an employee"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LoanService(db)
    
    try:
        loans = service.get_active_loans_for_employee(
            company_id=current_user.company_id,
            employee_id=employee_id
        )
        
        return {
            "success": True,
            "count": len(loans),
            "loans": loans
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LOAN APPROVAL & DISBURSEMENT
# ============================================================================

@router.post("/{loan_id}/approve")
def approve_loan(
    loan_id: str,
    data: LoanApprovalRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Approve loan application"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LoanService(db)
    
    try:
        loan = service.approve_loan(
            company_id=current_user.company_id,
            loan_id=loan_id,
            approved_by=current_user.id,
            approval_notes=data.approval_notes
        )
        
        return {
            "success": True,
            "message": "Loan approved successfully",
            "loan": loan
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{loan_id}/reject")
def reject_loan(
    loan_id: str,
    data: LoanRejectionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Reject loan application"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LoanService(db)
    
    try:
        loan = service.reject_loan(
            company_id=current_user.company_id,
            loan_id=loan_id,
            rejected_by=current_user.id,
            rejection_reason=data.rejection_reason
        )
        
        return {
            "success": True,
            "message": "Loan rejected",
            "loan": loan
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{loan_id}/disburse")
def disburse_loan(
    loan_id: str,
    data: LoanDisbursementRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Disburse approved loan"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LoanService(db)
    
    try:
        loan = service.disburse_loan(
            company_id=current_user.company_id,
            loan_id=loan_id,
            disbursement_method=data.disbursement_method,
            disbursement_reference=data.disbursement_reference,
            disbursed_by=current_user.id
        )
        
        return {
            "success": True,
            "message": "Loan disbursed successfully",
            "loan": loan
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LOAN PAYMENTS
# ============================================================================

@router.post("/{loan_id}/payments")
def record_loan_payment(
    loan_id: str,
    data: LoanPaymentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Record manual loan payment"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LoanService(db)
    
    try:
        payment = service.record_payment(
            company_id=current_user.company_id,
            loan_id=loan_id,
            payment_amount=data.payment_amount,
            payment_date=data.payment_date,
            payment_method=data.payment_method,
            reference_number=data.reference_number,
            created_by=current_user.id,
            notes=data.notes
        )
        
        return {
            "success": True,
            "message": "Payment recorded successfully",
            "payment": payment
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{loan_id}/payments")
def get_loan_payments(
    loan_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get payment history for a loan"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Verify loan belongs to company
    loan = db.query(models.EmployeeLoan).filter(
        models.EmployeeLoan.id == loan_id,
        models.EmployeeLoan.company_id == current_user.company_id
    ).first()
    
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    try:
        payments = db.query(models.LoanPayment).filter(
            models.LoanPayment.loan_id == loan_id
        ).order_by(models.LoanPayment.payment_date).all()
        
        return {
            "success": True,
            "count": len(payments),
            "payments": payments
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PAYROLL INTEGRATION
# ============================================================================

@router.get("/payroll-deductions/{payment_date}")
def get_loans_for_payroll(
    payment_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get loans that need deduction for a payroll period"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = LoanService(db)
    
    try:
        deductions = service.get_loans_for_payroll_deduction(
            company_id=current_user.company_id,
            payment_date=payment_date
        )
        
        total_deductions = sum(d["monthly_payment"] for d in deductions)
        
        return {
            "success": True,
            "payment_date": payment_date,
            "count": len(deductions),
            "total_deductions": total_deductions,
            "deductions": deductions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

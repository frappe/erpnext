"""
Payroll API Routes

Endpoints for:
- Payrun management (create, calculate, validate, post, export)
- Payslip generation and distribution
- Salary components configuration
- Employee loans and advances
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel

import models
from database import get_db
from auth import get_current_user
from services.payroll.zambian_payroll_engine import PayrollService, ZambianPayrollEngine

router = APIRouter(prefix="/api/payroll", tags=["Payroll"])


class PayrunCreate(BaseModel):
    period_start: date
    period_end: date
    payment_date: date
    payrun_name: Optional[str] = None


class LoanCreate(BaseModel):
    employee_id: str
    loan_type: str
    principal_amount: float
    interest_rate: float = 0.0
    repayment_months: int
    repayment_start_date: date
    loan_purpose: Optional[str] = None
    notes: Optional[str] = None


class LoanApproval(BaseModel):
    approved: bool
    approval_notes: Optional[str] = None


@router.post("/payruns")
def create_payrun(
    data: PayrunCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new payrun"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = PayrollService(db)
    payrun = service.create_payrun(
        company_id=current_user.company_id,
        period_start=data.period_start,
        period_end=data.period_end,
        payment_date=data.payment_date,
        payrun_name=data.payrun_name,
        created_by=current_user.id
    )
    
    return {"success": True, "payrun": payrun}


@router.post("/payruns/{payrun_id}/calculate")
def calculate_payrun(
    payrun_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Calculate payroll for all employees"""
    service = PayrollService(db)
    
    try:
        payrun = service.calculate_payrun(payrun_id)
        
        return {
            "success": True,
            "payrun": payrun,
            "summary": {
                "total_gross": payrun.total_gross,
                "total_net": payrun.total_net,
                "total_paye": payrun.total_paye,
                "total_napsa": payrun.total_napsa_employee + payrun.total_napsa_employer,
                "total_nhima": payrun.total_nhima_employee + payrun.total_nhima_employer,
                "total_employer_cost": payrun.total_employer_cost
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payruns")
def list_payruns(
    status: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all payruns"""
    query = db.query(models.Payrun).filter(
        models.Payrun.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.Payrun.status == status)
    if year:
        query = query.filter(
            models.Payrun.period_start >= date(year, 1, 1),
            models.Payrun.period_end <= date(year, 12, 31)
        )
    
    payruns = query.order_by(models.Payrun.period_start.desc()).all()
    
    return {"success": True, "count": len(payruns), "payruns": payruns}


@router.get("/payruns/{payrun_id}")
def get_payrun(
    payrun_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get payrun details"""
    payrun = db.query(models.Payrun).filter(
        models.Payrun.id == payrun_id,
        models.Payrun.company_id == current_user.company_id
    ).first()
    
    if not payrun:
        raise HTTPException(status_code=404, detail="Payrun not found")
    
    # Get payslips
    payslips = db.query(models.Payslip).filter(
        models.Payslip.payrun_id == payrun_id
    ).all()
    
    return {
        "success": True,
        "payrun": payrun,
        "payslips_count": len(payslips),
        "payslips": payslips
    }


@router.get("/payruns/{payrun_id}/payslips")
def get_payrun_payslips(
    payrun_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all payslips for a payrun"""
    payslips = db.query(models.Payslip).filter(
        models.Payslip.payrun_id == payrun_id,
        models.Payslip.company_id == current_user.company_id
    ).all()
    
    return {"success": True, "count": len(payslips), "payslips": payslips}


@router.get("/payslips/employee/{employee_id}")
def get_employee_payslips(
    employee_id: str,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get payslips for an employee"""
    query = db.query(models.Payslip).join(models.Payrun).filter(
        models.Payslip.employee_id == employee_id,
        models.Payslip.company_id == current_user.company_id
    )
    
    if year:
        query = query.filter(
            models.Payrun.period_start >= date(year, 1, 1),
            models.Payrun.period_end <= date(year, 12, 31)
        )
    
    payslips = query.order_by(models.Payrun.period_start.desc()).all()
    
    return {"success": True, "count": len(payslips), "payslips": payslips}


@router.post("/loans")
def create_loan(
    data: LoanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create employee loan or salary advance"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Verify employee
    employee = db.query(models.Employee).filter(
        models.Employee.id == data.employee_id,
        models.Employee.company_id == current_user.company_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Calculate total amount with interest
    if data.interest_rate > 0:
        # Simple interest calculation
        interest = data.principal_amount * (data.interest_rate / 100) * (data.repayment_months / 12)
        total_amount = data.principal_amount + interest
    else:
        total_amount = data.principal_amount
    
    # Calculate monthly repayment
    repayment_amount = total_amount / data.repayment_months
    
    # Generate loan number
    last_loan = db.query(models.EmployeeLoan).filter(
        models.EmployeeLoan.company_id == current_user.company_id
    ).order_by(models.EmployeeLoan.created_at.desc()).first()
    
    if last_loan and last_loan.loan_number:
        try:
            last_num = int(last_loan.loan_number.split('-')[1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    loan_number = f"LOAN-{new_num:05d}"
    
    # Create loan
    loan = models.EmployeeLoan(
        company_id=current_user.company_id,
        employee_id=data.employee_id,
        loan_number=loan_number,
        loan_type=data.loan_type,
        loan_purpose=data.loan_purpose,
        principal_amount=data.principal_amount,
        interest_rate=data.interest_rate,
        total_amount=total_amount,
        outstanding_balance=total_amount,
        repayment_amount=repayment_amount,
        repayment_start_date=data.repayment_start_date,
        repayment_months=data.repayment_months,
        remaining_months=data.repayment_months,
        status="pending",
        notes=data.notes,
        created_by=current_user.id
    )
    
    db.add(loan)
    db.commit()
    db.refresh(loan)
    
    return {"success": True, "loan": loan}


@router.put("/loans/{loan_id}/approve")
def approve_loan(
    loan_id: str,
    data: LoanApproval,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Approve or reject loan"""
    loan = db.query(models.EmployeeLoan).filter(
        models.EmployeeLoan.id == loan_id,
        models.EmployeeLoan.company_id == current_user.company_id
    ).first()
    
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    if loan.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot approve loan in status: {loan.status}")
    
    loan.approved_by = current_user.id
    loan.approved_date = date.today()
    loan.approval_notes = data.approval_notes
    
    if data.approved:
        loan.status = "approved"
    else:
        loan.status = "rejected"
    
    db.commit()
    db.refresh(loan)
    
    return {"success": True, "loan": loan}


@router.get("/loans")
def list_loans(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List loans"""
    query = db.query(models.EmployeeLoan).filter(
        models.EmployeeLoan.company_id == current_user.company_id
    )
    
    if employee_id:
        query = query.filter(models.EmployeeLoan.employee_id == employee_id)
    if status:
        query = query.filter(models.EmployeeLoan.status == status)
    
    loans = query.order_by(models.EmployeeLoan.created_at.desc()).all()
    
    return {"success": True, "count": len(loans), "loans": loans}


@router.get("/statutory-report/{year}/{month}")
def get_statutory_report(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get statutory report (PAYE, NAPSA, NHIMA totals) for a month"""
    # Get payrun for the period
    period_start = date(year, month, 1)
    
    payrun = db.query(models.Payrun).filter(
        models.Payrun.company_id == current_user.company_id,
        models.Payrun.period_start == period_start
    ).first()
    
    if not payrun:
        return {
            "success": True,
            "message": "No payrun found for this period",
            "report": None
        }
    
    return {
        "success": True,
        "report": {
            "period": f"{year}-{month:02d}",
            "payrun_number": payrun.payrun_number,
            "paye": {
                "total": payrun.total_paye,
                "due_date": date(year if month < 12 else year + 1, month + 1 if month < 12 else 1, 10)
            },
            "napsa": {
                "employee": payrun.total_napsa_employee,
                "employer": payrun.total_napsa_employer,
                "total": payrun.total_napsa_employee + payrun.total_napsa_employer,
                "due_date": date(year if month < 12 else year + 1, month + 1 if month < 12 else 1, 10)
            },
            "nhima": {
                "employee": payrun.total_nhima_employee,
                "employer": payrun.total_nhima_employer,
                "total": payrun.total_nhima_employee + payrun.total_nhima_employer,
                "due_date": date(year if month < 12 else year + 1, month + 1 if month < 12 else 1, 10)
            },
            "summary": {
                "total_gross": payrun.total_gross,
                "total_net": payrun.total_net,
                "total_employer_cost": payrun.total_employer_cost
            }
        }
    }

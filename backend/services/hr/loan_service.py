"""
Employee Loan & Advances Service

Handles:
- Loan creation with repayment schedules
- Interest calculation (simple & compound)
- Loan approval workflow
- Disbursement tracking
- Payment processing
- Balance tracking
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException
import models
from dateutil.relativedelta import relativedelta
import random


class LoanService:
    """Manages employee loans and advances"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # LOAN CREATION & MANAGEMENT
    # ========================================================================
    
    def create_loan(
        self,
        company_id: str,
        employee_id: str,
        loan_type: str,
        principal_amount: float,
        interest_rate: float,
        repayment_months: int,
        repayment_start_date: date,
        loan_purpose: Optional[str] = None,
        created_by: str = None,
        notes: Optional[str] = None
    ) -> models.EmployeeLoan:
        """Create new employee loan with amortization schedule"""
        
        # Validate employee exists
        employee = self.db.query(models.Employee).filter(
            models.Employee.id == employee_id,
            models.Employee.company_id == company_id,
            models.Employee.status == "active"
        ).first()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Active employee not found")
        
        # Validate amounts
        if principal_amount <= 0:
            raise HTTPException(status_code=400, detail="Principal amount must be positive")
        
        if interest_rate < 0:
            raise HTTPException(status_code=400, detail="Interest rate cannot be negative")
        
        if repayment_months <= 0:
            raise HTTPException(status_code=400, detail="Repayment months must be positive")
        
        # Generate loan number
        loan_number = self._generate_loan_number(company_id)
        
        # Calculate total amount and monthly repayment
        if interest_rate > 0:
            # Calculate using reducing balance method
            monthly_rate = interest_rate / 100 / 12
            total_amount = principal_amount * (1 + (monthly_rate * repayment_months))
            monthly_payment = total_amount / repayment_months
        else:
            # No interest
            total_amount = principal_amount
            monthly_payment = principal_amount / repayment_months
        
        # Generate amortization schedule
        amortization_schedule = self._generate_amortization_schedule(
            principal=principal_amount,
            interest_rate=interest_rate,
            months=repayment_months,
            start_date=repayment_start_date
        )
        
        # Create loan
        loan = models.EmployeeLoan(
            company_id=company_id,
            employee_id=employee_id,
            loan_number=loan_number,
            loan_type=loan_type,
            loan_purpose=loan_purpose,
            principal_amount=principal_amount,
            interest_rate=interest_rate,
            total_amount=total_amount,
            outstanding_balance=total_amount,
            repayment_amount=monthly_payment,
            repayment_start_date=repayment_start_date,
            repayment_months=repayment_months,
            remaining_months=repayment_months,
            amortization_schedule=amortization_schedule,
            requested_date=date.today(),
            status="pending",
            notes=notes,
            created_by=created_by
        )
        
        self.db.add(loan)
        self.db.commit()
        self.db.refresh(loan)
        
        return loan
    
    def _generate_loan_number(self, company_id: str) -> str:
        """Generate unique loan number"""
        # Get count of loans for this company
        count = self.db.query(func.count(models.EmployeeLoan.id)).filter(
            models.EmployeeLoan.company_id == company_id
        ).scalar()
        
        # Format: LOAN-YYYYMMDD-XXXX
        today = date.today().strftime('%Y%m%d')
        sequence = str(count + 1).zfill(4)
        
        return f"LOAN-{today}-{sequence}"
    
    def _generate_amortization_schedule(
        self,
        principal: float,
        interest_rate: float,
        months: int,
        start_date: date
    ) -> List[Dict]:
        """Generate loan amortization schedule"""
        
        schedule = []
        balance = principal
        monthly_rate = interest_rate / 100 / 12 if interest_rate > 0 else 0
        
        # Calculate monthly payment
        if monthly_rate > 0:
            monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / \
                            ((1 + monthly_rate) ** months - 1)
        else:
            monthly_payment = principal / months
        
        for month in range(1, months + 1):
            # Calculate interest for this period
            interest_payment = balance * monthly_rate
            principal_payment = monthly_payment - interest_payment
            
            # Update balance
            balance = max(0, balance - principal_payment)
            
            # Calculate payment date
            payment_date = start_date + relativedelta(months=month - 1)
            
            schedule.append({
                "month": month,
                "payment_date": payment_date.isoformat(),
                "opening_balance": round(balance + principal_payment, 2),
                "monthly_payment": round(monthly_payment, 2),
                "principal_payment": round(principal_payment, 2),
                "interest_payment": round(interest_payment, 2),
                "closing_balance": round(balance, 2),
                "paid": False
            })
        
        return schedule
    
    # ========================================================================
    # LOAN APPROVAL & DISBURSEMENT
    # ========================================================================
    
    def approve_loan(
        self,
        company_id: str,
        loan_id: str,
        approved_by: str,
        approval_notes: Optional[str] = None
    ) -> models.EmployeeLoan:
        """Approve loan application"""
        
        loan = self.db.query(models.EmployeeLoan).filter(
            models.EmployeeLoan.id == loan_id,
            models.EmployeeLoan.company_id == company_id,
            models.EmployeeLoan.status == "pending"
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Pending loan not found")
        
        loan.status = "approved"
        loan.approved_by = approved_by
        loan.approved_date = date.today()
        loan.approval_notes = approval_notes
        
        self.db.commit()
        self.db.refresh(loan)
        
        return loan
    
    def reject_loan(
        self,
        company_id: str,
        loan_id: str,
        rejected_by: str,
        rejection_reason: str
    ) -> models.EmployeeLoan:
        """Reject loan application"""
        
        loan = self.db.query(models.EmployeeLoan).filter(
            models.EmployeeLoan.id == loan_id,
            models.EmployeeLoan.company_id == company_id,
            models.EmployeeLoan.status == "pending"
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Pending loan not found")
        
        loan.status = "rejected"
        loan.approved_by = rejected_by
        loan.approved_date = date.today()
        loan.approval_notes = rejection_reason
        
        self.db.commit()
        self.db.refresh(loan)
        
        return loan
    
    def disburse_loan(
        self,
        company_id: str,
        loan_id: str,
        disbursement_method: str,
        disbursement_reference: Optional[str] = None,
        disbursed_by: str = None
    ) -> models.EmployeeLoan:
        """Mark loan as disbursed and activate"""
        
        loan = self.db.query(models.EmployeeLoan).filter(
            models.EmployeeLoan.id == loan_id,
            models.EmployeeLoan.company_id == company_id,
            models.EmployeeLoan.status == "approved"
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Approved loan not found")
        
        loan.status = "active"
        loan.disbursed_date = date.today()
        loan.disbursement_method = disbursement_method
        loan.disbursement_reference = disbursement_reference
        
        self.db.commit()
        self.db.refresh(loan)
        
        return loan
    
    # ========================================================================
    # LOAN PAYMENTS
    # ========================================================================
    
    def record_payment(
        self,
        company_id: str,
        loan_id: str,
        payment_amount: float,
        payment_date: date,
        payment_method: str = "payroll_deduction",
        payrun_id: Optional[str] = None,
        reference_number: Optional[str] = None,
        created_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> models.LoanPayment:
        """Record a loan payment"""
        
        # Get loan
        loan = self.db.query(models.EmployeeLoan).filter(
            models.EmployeeLoan.id == loan_id,
            models.EmployeeLoan.company_id == company_id
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Loan not found")
        
        if loan.status not in ["active", "disbursed"]:
            raise HTTPException(status_code=400, detail="Loan is not active")
        
        # Calculate payment breakdown
        monthly_rate = loan.interest_rate / 100 / 12 if loan.interest_rate > 0 else 0
        interest_paid = loan.outstanding_balance * monthly_rate
        principal_paid = payment_amount - interest_paid
        
        # Update loan balance
        new_balance = max(0, loan.outstanding_balance - payment_amount)
        
        # Determine payment number
        payment_count = self.db.query(func.count(models.LoanPayment.id)).filter(
            models.LoanPayment.loan_id == loan_id
        ).scalar()
        payment_number = payment_count + 1
        
        # Create payment record
        payment = models.LoanPayment(
            company_id=company_id,
            loan_id=loan_id,
            employee_id=loan.employee_id,
            payment_date=payment_date,
            payment_number=payment_number,
            payment_amount=payment_amount,
            principal_paid=principal_paid,
            interest_paid=interest_paid,
            balance_after_payment=new_balance,
            payrun_id=payrun_id,
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            created_by=created_by
        )
        
        self.db.add(payment)
        
        # Update loan
        loan.outstanding_balance = new_balance
        loan.remaining_months = max(0, loan.remaining_months - 1)
        
        # Mark loan as completed if fully paid
        if new_balance <= 0.01:  # Allow for rounding errors
            loan.status = "completed"
            loan.outstanding_balance = 0
            loan.remaining_months = 0
        
        # Update amortization schedule
        if loan.amortization_schedule and payment_number <= len(loan.amortization_schedule):
            loan.amortization_schedule[payment_number - 1]["paid"] = True
        
        self.db.commit()
        self.db.refresh(payment)
        self.db.refresh(loan)
        
        return payment
    
    # ========================================================================
    # QUERIES & REPORTS
    # ========================================================================
    
    def get_active_loans_for_employee(
        self,
        company_id: str,
        employee_id: str
    ) -> List[models.EmployeeLoan]:
        """Get all active loans for an employee"""
        
        loans = self.db.query(models.EmployeeLoan).filter(
            models.EmployeeLoan.company_id == company_id,
            models.EmployeeLoan.employee_id == employee_id,
            models.EmployeeLoan.status.in_(["active", "disbursed"])
        ).order_by(models.EmployeeLoan.created_at.desc()).all()
        
        return loans
    
    def get_loan_details(
        self,
        company_id: str,
        loan_id: str
    ) -> Dict:
        """Get detailed loan information including payment history"""
        
        loan = self.db.query(models.EmployeeLoan).filter(
            models.EmployeeLoan.id == loan_id,
            models.EmployeeLoan.company_id == company_id
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Loan not found")
        
        # Get payment history
        payments = self.db.query(models.LoanPayment).filter(
            models.LoanPayment.loan_id == loan_id
        ).order_by(models.LoanPayment.payment_date).all()
        
        # Calculate totals
        total_paid = sum(p.payment_amount for p in payments)
        total_principal_paid = sum(p.principal_paid for p in payments)
        total_interest_paid = sum(p.interest_paid for p in payments)
        
        return {
            "loan": loan,
            "payments": payments,
            "summary": {
                "total_paid": total_paid,
                "total_principal_paid": total_principal_paid,
                "total_interest_paid": total_interest_paid,
                "outstanding_balance": loan.outstanding_balance,
                "payments_made": len(payments),
                "payments_remaining": loan.remaining_months
            }
        }
    
    def get_company_loans(
        self,
        company_id: str,
        status: Optional[str] = None,
        employee_id: Optional[str] = None
    ) -> List[models.EmployeeLoan]:
        """Get all loans for a company with optional filters"""
        
        query = self.db.query(models.EmployeeLoan).filter(
            models.EmployeeLoan.company_id == company_id
        )
        
        if status:
            query = query.filter(models.EmployeeLoan.status == status)
        
        if employee_id:
            query = query.filter(models.EmployeeLoan.employee_id == employee_id)
        
        return query.order_by(models.EmployeeLoan.created_at.desc()).all()
    
    def get_loans_for_payroll_deduction(
        self,
        company_id: str,
        payment_date: date
    ) -> List[Dict]:
        """Get loans that need deduction for a specific payroll period"""
        
        # Get all active loans where repayment_start_date <= payment_date
        loans = self.db.query(models.EmployeeLoan).filter(
            models.EmployeeLoan.company_id == company_id,
            models.EmployeeLoan.status == "active",
            models.EmployeeLoan.repayment_start_date <= payment_date,
            models.EmployeeLoan.outstanding_balance > 0
        ).all()
        
        deductions = []
        for loan in loans:
            # Check if payment already made this period
            # For simplicity, we'll deduct if outstanding balance > 0
            deductions.append({
                "loan_id": loan.id,
                "employee_id": loan.employee_id,
                "loan_number": loan.loan_number,
                "loan_type": loan.loan_type,
                "monthly_payment": loan.repayment_amount,
                "outstanding_balance": loan.outstanding_balance,
                "remaining_months": loan.remaining_months
            })
        
        return deductions

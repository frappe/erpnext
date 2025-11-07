"""
Payroll Run Service

Handles batch payroll processing:
- Create payroll runs (periods)
- Process employees in batch
- Generate payslips
- Calculate totals and summaries
- Validate and approve payroll
- Integration with attendance and leave
"""

from datetime import datetime, date
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException
import models
from services.payroll.zambian_payroll_engine import ZambianPayrollEngine


class PayrollRunService:
    """Manages payroll run batch processing"""
    
    def __init__(self, db: Session):
        self.db = db
        self.payroll_engine = ZambianPayrollEngine()
    
    # ========================================================================
    # PAYROLL RUN CREATION
    # ========================================================================
    
    def create_payroll_run(
        self,
        company_id: str,
        period_start: date,
        period_end: date,
        payment_date: date,
        payrun_name: Optional[str] = None,
        created_by: str = None
    ) -> Dict:
        """Create a new payroll run"""
        
        # Generate payrun number
        payrun_number = self._generate_payrun_number(company_id, period_start)
        
        # Check for duplicate period
        existing = self.db.query(models.Payrun).filter(
            models.Payrun.company_id == company_id,
            models.Payrun.period_start == period_start,
            models.Payrun.period_end == period_end,
            models.Payrun.status != "archived"
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Payroll run already exists for this period: {payrun_number}"
            )
        
        # Create payrun
        payrun = models.Payrun(
            company_id=company_id,
            payrun_number=payrun_number,
            payrun_name=payrun_name or f"Payroll - {period_start.strftime('%B %Y')}",
            period_start=period_start,
            period_end=period_end,
            payment_date=payment_date,
            status="draft",
            created_by=created_by,
            currency="ZMW",
            exchange_rate=1.0
        )
        
        self.db.add(payrun)
        self.db.commit()
        self.db.refresh(payrun)
        
        return self._payrun_to_dict(payrun)
    
    def _generate_payrun_number(self, company_id: str, period_start: date) -> str:
        """Generate unique payrun number"""
        prefix = f"PR-{period_start.strftime('%Y%m')}"
        
        # Find last number for this month
        last_payrun = self.db.query(models.Payrun).filter(
            models.Payrun.company_id == company_id,
            models.Payrun.payrun_number.like(f"{prefix}%")
        ).order_by(models.Payrun.payrun_number.desc()).first()
        
        if last_payrun:
            try:
                last_num = int(last_payrun.payrun_number.split("-")[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f"{prefix}-{next_num:03d}"
    
    # ========================================================================
    # BATCH PROCESSING
    # ========================================================================
    
    def process_payroll_run(
        self,
        company_id: str,
        payrun_id: str,
        employee_ids: Optional[List[str]] = None
    ) -> Dict:
        """Process payroll for all employees in the run"""
        
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id,
            models.Payrun.company_id == company_id
        ).first()
        
        if not payrun:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        if payrun.status not in ["draft", "validated"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot process payroll with status: {payrun.status}"
            )
        
        # Get employees to process
        if employee_ids:
            employees = self.db.query(models.Employee).filter(
                models.Employee.company_id == company_id,
                models.Employee.id.in_(employee_ids),
                models.Employee.status == "active"
            ).all()
        else:
            employees = self.db.query(models.Employee).filter(
                models.Employee.company_id == company_id,
                models.Employee.status == "active"
            ).all()
        
        if not employees:
            raise HTTPException(status_code=400, detail="No active employees found")
        
        # Process each employee
        processed = 0
        errors = []
        payslips = []
        
        for employee in employees:
            try:
                payslip = self._process_employee_payslip(
                    company_id=company_id,
                    payrun=payrun,
                    employee=employee
                )
                payslips.append(payslip)
                processed += 1
            except Exception as e:
                errors.append({
                    "employee_id": employee.id,
                    "employee_name": f"{employee.first_name} {employee.last_name}",
                    "error": str(e)
                })
        
        # Calculate totals
        self._calculate_payrun_totals(payrun)
        
        # Update status
        if errors:
            payrun.validation_errors = errors
        
        self.db.commit()
        self.db.refresh(payrun)
        
        return {
            "payrun": self._payrun_to_dict(payrun),
            "processed": processed,
            "total_employees": len(employees),
            "errors": errors,
            "payslips_count": len(payslips)
        }
    
    def _process_employee_payslip(
        self,
        company_id: str,
        payrun: models.Payrun,
        employee: models.Employee
    ) -> models.Payslip:
        """Process payslip for a single employee"""
        
        # Delete existing payslip if reprocessing
        existing = self.db.query(models.Payslip).filter(
            models.Payslip.payrun_id == payrun.id,
            models.Payslip.employee_id == employee.id
        ).first()
        
        if existing:
            self.db.delete(existing)
            self.db.flush()
        
        # Get attendance data
        attendance_summary = self._get_attendance_summary(
            company_id=company_id,
            employee_id=employee.id,
            period_start=payrun.period_start,
            period_end=payrun.period_end
        )
        
        # Get leave data
        leave_summary = self._get_leave_summary(
            company_id=company_id,
            employee_id=employee.id,
            period_start=payrun.period_start,
            period_end=payrun.period_end
        )
        
        # Calculate payroll using Zambian engine
        payroll_calc = self.payroll_engine.calculate_payroll(
            gross_salary=employee.basic_salary or 0.0,
            taxable_allowances=0.0,  # TODO: Add allowances from employee
            non_taxable_allowances=0.0
        )
        
        # Adjust for unpaid leave
        unpaid_leave_days = leave_summary.get("unpaid_days", 0)
        if unpaid_leave_days > 0:
            # Calculate daily rate (assuming 22 working days per month)
            daily_rate = employee.basic_salary / 22.0
            unpaid_deduction = daily_rate * unpaid_leave_days
            payroll_calc["net_pay"] -= unpaid_deduction
        else:
            unpaid_deduction = 0.0
        
        # Get employee loans/advances
        loan_deductions = self._get_loan_deductions(
            company_id=company_id,
            employee_id=employee.id,
            payrun_id=payrun.id
        )
        
        # Calculate final net pay
        total_loan_deductions = sum(loan_deductions.values())
        final_net_pay = payroll_calc["net_pay"] - total_loan_deductions
        
        # Create payslip
        payslip = models.Payslip(
            company_id=company_id,
            payrun_id=payrun.id,
            employee_id=employee.id,
            
            # Employee snapshot
            employee_name=f"{employee.first_name} {employee.last_name}",
            employee_number=employee.employee_no,
            department_name=employee.department_id,  # TODO: Get actual department name
            position=employee.position,
            
            # Earnings
            basic_salary=employee.basic_salary or 0.0,
            earnings_json={
                "basic_salary": employee.basic_salary or 0.0,
                "allowances": {}
            },
            total_earnings=employee.basic_salary or 0.0,
            
            # Deductions
            deductions_json={
                "paye": payroll_calc["paye"],
                "napsa_employee": payroll_calc["napsa_employee"],
                "nhima_employee": payroll_calc["nhima_employee"],
                "workers_comp_employee": payroll_calc.get("workers_comp_employee", 0.0),
                "unpaid_leave": unpaid_deduction,
                "loans": loan_deductions
            },
            total_deductions=payroll_calc["total_deductions"] + unpaid_deduction + total_loan_deductions,
            
            # Statutory
            paye=payroll_calc["paye"],
            napsa_employee=payroll_calc["napsa_employee"],
            napsa_employer=payroll_calc["napsa_employer"],
            nhima_employee=payroll_calc["nhima_employee"],
            nhima_employer=payroll_calc["nhima_employer"],
            workers_comp_employee=payroll_calc.get("workers_comp_employee", 0.0),
            workers_comp_employer=payroll_calc.get("workers_comp_employer", 0.0),
            
            # Net pay
            net_pay=final_net_pay,
            
            # Attendance
            attendance_days=attendance_summary.get("present_days", 0),
            leave_days=leave_summary.get("total_days", 0),
            unpaid_leave_days=unpaid_leave_days,
            overtime_hours=attendance_summary.get("overtime_hours", 0.0),
            
            # Status
            status="draft",
            
            # Currency
            currency="ZMW",
            exchange_rate=1.0
        )
        
        self.db.add(payslip)
        self.db.flush()
        
        return payslip
    
    def _get_attendance_summary(
        self,
        company_id: str,
        employee_id: str,
        period_start: date,
        period_end: date
    ) -> Dict:
        """Get attendance summary for the period"""
        from services.hr.attendance_service import AttendanceService
        
        try:
            service = AttendanceService(self.db)
            summary = service.get_attendance_summary(
                company_id=company_id,
                employee_id=employee_id,
                start_date=period_start,
                end_date=period_end
            )
            return summary
        except Exception:
            # Return defaults if no attendance data
            return {
                "present_days": 0,
                "absent_days": 0,
                "overtime_hours": 0.0
            }
    
    def _get_leave_summary(
        self,
        company_id: str,
        employee_id: str,
        period_start: date,
        period_end: date
    ) -> Dict:
        """Get leave summary for the period"""
        
        # Get approved leave requests in this period
        leave_requests = self.db.query(models.LeaveApplication).filter(
            models.LeaveApplication.company_id == company_id,
            models.LeaveApplication.employee_id == employee_id,
            models.LeaveApplication.status == "approved",
            models.LeaveApplication.start_date <= period_end,
            models.LeaveApplication.end_date >= period_start
        ).all()
        
        total_days = 0.0
        unpaid_days = 0.0
        
        for leave_req in leave_requests:
            # Get leave type to check if paid
            leave_type = self.db.query(models.LeaveType).filter(
                models.LeaveType.id == leave_req.leave_type_id
            ).first()
            
            # Calculate overlapping days
            overlap_start = max(leave_req.start_date, period_start)
            overlap_end = min(leave_req.end_date, period_end)
            days = (overlap_end - overlap_start).days + 1
            
            total_days += days
            
            if leave_type and not leave_type.is_paid:
                unpaid_days += days
        
        return {
            "total_days": total_days,
            "unpaid_days": unpaid_days
        }
    
    def _get_loan_deductions(
        self,
        company_id: str,
        employee_id: str,
        payrun_id: str
    ) -> Dict[str, float]:
        """Get loan deductions for the employee"""
        
        from services.hr.loan_service import LoanService
        
        try:
            # Get payrun to determine payment date
            payrun = self.db.query(models.Payrun).filter(
                models.Payrun.id == payrun_id
            ).first()
            
            if not payrun:
                return {}
            
            # Get active loans for this employee
            loan_service = LoanService(self.db)
            active_loans = loan_service.get_active_loans_for_employee(
                company_id=company_id,
                employee_id=employee_id
            )
            
            # Build deductions dictionary
            deductions = {}
            for loan in active_loans:
                # Only deduct if repayment has started and balance remains
                if loan.repayment_start_date <= payrun.payment_date and loan.outstanding_balance > 0:
                    # Determine deduction amount (lesser of monthly payment or remaining balance)
                    deduction_amount = min(loan.repayment_amount, loan.outstanding_balance)
                    
                    # Use loan number as key for clarity
                    key = f"{loan.loan_type}_{loan.loan_number}"
                    deductions[key] = deduction_amount
            
            return deductions
        except Exception as e:
            # Log error but don't fail payroll processing
            print(f"Error getting loan deductions: {str(e)}")
            return {}
    
    def _record_loan_payments_for_payrun(
        self,
        company_id: str,
        payrun_id: str,
        payment_date: date,
        created_by: str
    ):
        """Record loan payments for all employees in this payroll run"""
        
        from services.hr.loan_service import LoanService
        
        try:
            # Get all payslips for this payrun
            payslips = self.db.query(models.Payslip).filter(
                models.Payslip.payrun_id == payrun_id
            ).all()
            
            loan_service = LoanService(self.db)
            
            for payslip in payslips:
                # Check if payslip has loan deductions
                if not payslip.deductions_json or "loans" not in payslip.deductions_json:
                    continue
                
                loan_deductions = payslip.deductions_json.get("loans", {})
                if not loan_deductions:
                    continue
                
                # Get active loans for this employee
                active_loans = loan_service.get_active_loans_for_employee(
                    company_id=company_id,
                    employee_id=payslip.employee_id
                )
                
                # Record payment for each loan
                for loan in active_loans:
                    loan_key = f"{loan.loan_type}_{loan.loan_number}"
                    
                    if loan_key in loan_deductions:
                        payment_amount = loan_deductions[loan_key]
                        
                        if payment_amount > 0:
                            try:
                                loan_service.record_payment(
                                    company_id=company_id,
                                    loan_id=loan.id,
                                    payment_amount=payment_amount,
                                    payment_date=payment_date,
                                    payment_method="payroll_deduction",
                                    payrun_id=payrun_id,
                                    reference_number=f"Payroll-{payrun_id}",
                                    created_by=created_by,
                                    notes=f"Automatic deduction from payroll {payslip.employee_number}"
                                )
                            except Exception as e:
                                print(f"Error recording loan payment for employee {payslip.employee_id}: {str(e)}")
        
        except Exception as e:
            print(f"Error processing loan payments for payrun: {str(e)}")
    
    def _calculate_payrun_totals(self, payrun: models.Payrun):
        """Calculate and update payrun totals"""
        
        payslips = self.db.query(models.Payslip).filter(
            models.Payslip.payrun_id == payrun.id
        ).all()
        
        payrun.total_gross = sum(p.total_earnings for p in payslips)
        payrun.total_deductions = sum(p.total_deductions for p in payslips)
        payrun.total_net = sum(p.net_pay for p in payslips)
        
        payrun.total_paye = sum(p.paye for p in payslips)
        payrun.total_napsa_employee = sum(p.napsa_employee for p in payslips)
        payrun.total_napsa_employer = sum(p.napsa_employer for p in payslips)
        payrun.total_nhima_employee = sum(p.nhima_employee for p in payslips)
        payrun.total_nhima_employer = sum(p.nhima_employer for p in payslips)
        
        # Calculate total employer cost
        payrun.total_employer_cost = (
            payrun.total_gross +
            payrun.total_napsa_employer +
            payrun.total_nhima_employer
        )
    
    # ========================================================================
    # PAYROLL VALIDATION & APPROVAL
    # ========================================================================
    
    def validate_payroll_run(
        self,
        company_id: str,
        payrun_id: str,
        validated_by: str
    ) -> Dict:
        """Validate payroll run"""
        
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id,
            models.Payrun.company_id == company_id
        ).first()
        
        if not payrun:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        if payrun.status != "draft":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot validate payroll with status: {payrun.status}"
            )
        
        # Run validation checks
        errors = []
        
        # Check if payslips exist
        payslip_count = self.db.query(func.count(models.Payslip.id)).filter(
            models.Payslip.payrun_id == payrun.id
        ).scalar()
        
        if payslip_count == 0:
            errors.append("No payslips found. Please process the payroll first.")
        
        # Check for negative net pay
        negative_payslips = self.db.query(models.Payslip).filter(
            models.Payslip.payrun_id == payrun.id,
            models.Payslip.net_pay < 0
        ).all()
        
        if negative_payslips:
            for ps in negative_payslips:
                errors.append(f"Negative net pay for {ps.employee_name}: {ps.net_pay}")
        
        if errors:
            payrun.validation_errors = errors
            payrun.status = "draft"
        else:
            payrun.validation_errors = None
            payrun.status = "validated"
            payrun.validated_at = datetime.utcnow()
            payrun.validated_by = validated_by
        
        self.db.commit()
        self.db.refresh(payrun)
        
        return {
            "success": len(errors) == 0,
            "status": payrun.status,
            "validation_errors": errors,
            "payrun": self._payrun_to_dict(payrun)
        }
    
    def approve_payroll_run(
        self,
        company_id: str,
        payrun_id: str,
        approved_by: str
    ) -> Dict:
        """Approve and finalize payroll run"""
        
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id,
            models.Payrun.company_id == company_id
        ).first()
        
        if not payrun:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        if payrun.status != "validated":
            raise HTTPException(
                status_code=400,
                detail="Payroll must be validated before approval"
            )
        
        # Update all payslips to approved
        self.db.query(models.Payslip).filter(
            models.Payslip.payrun_id == payrun.id
        ).update({"status": "approved"})
        
        # Record loan payments for this payroll run
        self._record_loan_payments_for_payrun(
            company_id=company_id,
            payrun_id=payrun.id,
            payment_date=payrun.payment_date,
            created_by=approved_by
        )
        
        # Mark payrun as posted (ready for GL posting and export)
        payrun.status = "posted"
        payrun.posted_at = datetime.utcnow()
        payrun.posted_by = approved_by
        
        self.db.commit()
        self.db.refresh(payrun)
        
        return {
            "success": True,
            "message": "Payroll approved successfully",
            "payrun": self._payrun_to_dict(payrun)
        }
    
    # ========================================================================
    # QUERY & REPORTING
    # ========================================================================
    
    def get_payroll_run(self, company_id: str, payrun_id: str) -> Dict:
        """Get payroll run details"""
        
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id,
            models.Payrun.company_id == company_id
        ).first()
        
        if not payrun:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        return self._payrun_to_dict(payrun, include_payslips=True)
    
    def list_payroll_runs(
        self,
        company_id: str,
        status: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[Dict]:
        """List payroll runs"""
        
        query = self.db.query(models.Payrun).filter(
            models.Payrun.company_id == company_id
        )
        
        if status:
            query = query.filter(models.Payrun.status == status)
        
        if year:
            query = query.filter(
                func.extract('year', models.Payrun.period_start) == year
            )
        
        payruns = query.order_by(models.Payrun.period_start.desc()).all()
        
        return [self._payrun_to_dict(pr) for pr in payruns]
    
    def get_payslips(
        self,
        company_id: str,
        payrun_id: str,
        employee_id: Optional[str] = None
    ) -> List[Dict]:
        """Get payslips for a payroll run"""
        
        query = self.db.query(models.Payslip).filter(
            models.Payslip.company_id == company_id,
            models.Payslip.payrun_id == payrun_id
        )
        
        if employee_id:
            query = query.filter(models.Payslip.employee_id == employee_id)
        
        payslips = query.all()
        
        return [self._payslip_to_dict(ps) for ps in payslips]
    
    def _payrun_to_dict(
        self,
        payrun: models.Payrun,
        include_payslips: bool = False
    ) -> Dict:
        """Convert payrun to dictionary"""
        result = {
            "id": payrun.id,
            "payrun_number": payrun.payrun_number,
            "payrun_name": payrun.payrun_name,
            "period_start": payrun.period_start.isoformat(),
            "period_end": payrun.period_end.isoformat(),
            "payment_date": payrun.payment_date.isoformat(),
            "currency": payrun.currency,
            "status": payrun.status,
            "total_gross": payrun.total_gross,
            "total_deductions": payrun.total_deductions,
            "total_net": payrun.total_net,
            "total_employer_cost": payrun.total_employer_cost,
            "statutory_totals": {
                "paye": payrun.total_paye,
                "napsa_employee": payrun.total_napsa_employee,
                "napsa_employer": payrun.total_napsa_employer,
                "nhima_employee": payrun.total_nhima_employee,
                "nhima_employer": payrun.total_nhima_employer
            },
            "validated_at": payrun.validated_at.isoformat() if payrun.validated_at else None,
            "posted_at": payrun.posted_at.isoformat() if payrun.posted_at else None,
            "validation_errors": payrun.validation_errors,
            "created_at": payrun.created_at.isoformat()
        }
        
        if include_payslips:
            payslips = self.db.query(models.Payslip).filter(
                models.Payslip.payrun_id == payrun.id
            ).all()
            result["payslips"] = [self._payslip_to_dict(ps) for ps in payslips]
            result["payslips_count"] = len(payslips)
        
        return result
    
    def _payslip_to_dict(self, payslip: models.Payslip) -> Dict:
        """Convert payslip to dictionary"""
        return {
            "id": payslip.id,
            "employee_id": payslip.employee_id,
            "employee_name": payslip.employee_name,
            "employee_number": payslip.employee_number,
            "department_name": payslip.department_name,
            "position": payslip.position,
            "basic_salary": payslip.basic_salary,
            "total_earnings": payslip.total_earnings,
            "total_deductions": payslip.total_deductions,
            "net_pay": payslip.net_pay,
            "paye": payslip.paye,
            "napsa_employee": payslip.napsa_employee,
            "napsa_employer": payslip.napsa_employer,
            "nhima_employee": payslip.nhima_employee,
            "nhima_employer": payslip.nhima_employer,
            "attendance_days": payslip.attendance_days,
            "leave_days": payslip.leave_days,
            "unpaid_leave_days": payslip.unpaid_leave_days,
            "overtime_hours": payslip.overtime_hours,
            "status": payslip.status,
            "earnings_breakdown": payslip.earnings_json,
            "deductions_breakdown": payslip.deductions_json
        }

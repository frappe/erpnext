"""
Zambian Payroll Engine - 2025 Rates

Implements accurate calculations for:
- PAYE (Pay As You Earn) tax - Progressive brackets
- NAPSA (National Pension Scheme Authority) - 5% employee + 5% employer
- NHIMA (National Health Insurance) - 0.5% employee + 0.5% employer

Calculation Order (CRITICAL):
1. Gross Pay = Basic Salary + Allowances
2. NAPSA (5% of gross, max ZMW 1,708.20)
3. Taxable Income = Gross - NAPSA
4. PAYE (progressive brackets on taxable income)
5. NHIMA (1% of gross split 0.5%/0.5%)
6. Other deductions
7. Net Pay = Gross - (NAPSA + PAYE + NHIMA + Other Deductions)
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

# ============================================================================
# 2025 ZAMBIA TAX & STATUTORY RATES
# ============================================================================

# PAYE Tax Brackets 2025 (Monthly)
PAYE_BRACKETS_2025_MONTHLY = [
    {"from": 0, "to": 5100, "rate": 0.00},      # 0% on first ZMW 5,100
    {"from": 5100, "to": 8200, "rate": 0.20},   # 20% on ZMW 5,101 - 8,200
    {"from": 8200, "to": 11200, "rate": 0.30},  # 30% on ZMW 8,201 - 11,200
    {"from": 11200, "to": None, "rate": 0.37}   # 37% above ZMW 11,200
]

# NAPSA 2025
NAPSA_EMPLOYEE_RATE = 0.05  # 5%
NAPSA_EMPLOYER_RATE = 0.05  # 5%
NAPSA_MONTHLY_CEILING = 34164.00  # Maximum earnings subject to NAPSA
NAPSA_MAX_EMPLOYEE_CONTRIBUTION = 1708.20  # 5% of 34,164
NAPSA_MAX_EMPLOYER_CONTRIBUTION = 1708.20  # 5% of 34,164

# NHIMA 2025
NHIMA_EMPLOYEE_RATE = 0.005  # 0.5%
NHIMA_EMPLOYER_RATE = 0.005  # 0.5%
NHIMA_TOTAL_RATE = 0.01      # 1% total

# Workers Compensation (approximate - varies by industry)
WORKERS_COMP_RATE = 0.01  # 1% (employer only)


class ZambianPayrollEngine:
    """Zambian payroll calculation engine with 2025 rates"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_employee_payroll(
        self,
        employee_id: str,
        period_start: date,
        period_end: date,
        basic_salary: float,
        allowances: Optional[Dict[str, float]] = None,
        other_deductions: Optional[Dict[str, float]] = None,
        loan_deductions: float = 0.0
    ) -> Dict:
        """
        Calculate complete payroll for an employee
        
        Returns detailed breakdown of earnings, statutory deductions, and net pay
        """
        employee = self.db.query(models.Employee).filter(
            models.Employee.id == employee_id
        ).first()
        
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
        
        # Initialize earnings
        earnings = {"basic_salary": basic_salary}
        if allowances:
            earnings.update(allowances)
        
        # Calculate gross pay
        gross_pay = sum(earnings.values())
        
        # NAPSA Calculation (on gross pay, before tax)
        napsa_employee, napsa_employer = self._calculate_napsa(
            gross_pay, 
            employee.napsa_exempted
        )
        
        # Taxable income (Gross - NAPSA employee contribution)
        taxable_income = gross_pay - napsa_employee
        
        # PAYE Calculation (on taxable income)
        paye = self._calculate_paye(taxable_income, employee.paye_exempted)
        
        # NHIMA Calculation (on gross pay)
        nhima_employee, nhima_employer = self._calculate_nhima(
            gross_pay,
            employee.nhima_exempted
        )
        
        # Workers Compensation (employer only)
        workers_comp = self._calculate_workers_comp(gross_pay)
        
        # Total statutory deductions (employee portion)
        statutory_deductions = {
            "napsa_employee": napsa_employee,
            "paye": paye,
            "nhima_employee": nhima_employee
        }
        
        # Total other deductions
        total_other_deductions = loan_deductions
        if other_deductions:
            total_other_deductions += sum(other_deductions.values())
        
        # Total deductions
        total_deductions = (
            napsa_employee + paye + nhima_employee + total_other_deductions
        )
        
        # Net pay
        net_pay = gross_pay - total_deductions
        
        # Employer costs (statutory contributions)
        employer_statutory = {
            "napsa_employer": napsa_employer,
            "nhima_employer": nhima_employer,
            "workers_comp": workers_comp
        }
        total_employer_cost = gross_pay + sum(employer_statutory.values())
        
        return {
            "employee_id": employee_id,
            "employee_name": f"{employee.first_name} {employee.last_name}",
            "employee_number": employee.employee_no,
            "period_start": period_start,
            "period_end": period_end,
            
            # Earnings
            "earnings": earnings,
            "gross_pay": gross_pay,
            
            # Statutory Deductions (Employee)
            "napsa_employee": napsa_employee,
            "taxable_income": taxable_income,
            "paye": paye,
            "nhima_employee": nhima_employee,
            
            # Other Deductions
            "loan_deductions": loan_deductions,
            "other_deductions": other_deductions or {},
            "total_other_deductions": total_other_deductions,
            
            # Totals
            "total_statutory_deductions": sum(statutory_deductions.values()),
            "total_deductions": total_deductions,
            "net_pay": net_pay,
            
            # Employer Costs
            "napsa_employer": napsa_employer,
            "nhima_employer": nhima_employer,
            "workers_comp": workers_comp,
            "total_employer_statutory": sum(employer_statutory.values()),
            "total_employer_cost": total_employer_cost,
            
            # Breakdown for reporting
            "statutory_breakdown": {
                "employee": statutory_deductions,
                "employer": employer_statutory
            }
        }
    
    def _calculate_napsa(self, gross_pay: float, is_exempted: bool = False) -> tuple:
        """
        Calculate NAPSA contributions (5% employee + 5% employer)
        
        2025 Rules:
        - 5% of gross pay (up to ceiling of ZMW 34,164)
        - Maximum contribution: ZMW 1,708.20 each
        """
        if is_exempted:
            return (0.0, 0.0)
        
        # Apply ceiling
        napsa_base = min(gross_pay, NAPSA_MONTHLY_CEILING)
        
        # Calculate contributions
        employee_contribution = napsa_base * NAPSA_EMPLOYEE_RATE
        employer_contribution = napsa_base * NAPSA_EMPLOYER_RATE
        
        # Apply maximum cap
        employee_contribution = min(employee_contribution, NAPSA_MAX_EMPLOYEE_CONTRIBUTION)
        employer_contribution = min(employer_contribution, NAPSA_MAX_EMPLOYER_CONTRIBUTION)
        
        return (round(employee_contribution, 2), round(employer_contribution, 2))
    
    def _calculate_paye(self, taxable_income: float, is_exempted: bool = False) -> float:
        """
        Calculate PAYE using 2025 progressive tax brackets
        
        Brackets (Monthly):
        - 0 - 5,100: 0%
        - 5,101 - 8,200: 20%
        - 8,201 - 11,200: 30%
        - Above 11,200: 37%
        """
        if is_exempted or taxable_income <= 0:
            return 0.0
        
        paye = 0.0
        remaining_income = taxable_income
        
        for i, bracket in enumerate(PAYE_BRACKETS_2025_MONTHLY):
            bracket_from = bracket["from"]
            bracket_to = bracket["to"]
            rate = bracket["rate"]
            
            if remaining_income <= 0:
                break
            
            # Calculate taxable amount in this bracket
            if bracket_to is None:
                # Last bracket (open-ended)
                taxable_in_bracket = remaining_income
            else:
                if remaining_income + bracket_from <= bracket_to:
                    taxable_in_bracket = remaining_income
                else:
                    taxable_in_bracket = bracket_to - bracket_from
            
            # Apply tax rate
            tax_in_bracket = taxable_in_bracket * rate
            paye += tax_in_bracket
            remaining_income -= taxable_in_bracket
        
        return round(paye, 2)
    
    def _calculate_nhima(self, gross_pay: float, is_exempted: bool = False) -> tuple:
        """
        Calculate NHIMA contributions (0.5% employee + 0.5% employer = 1% total)
        
        2025 Rules:
        - 1% of gross pay split equally
        - Employee: 0.5%
        - Employer: 0.5%
        """
        if is_exempted:
            return (0.0, 0.0)
        
        employee_contribution = gross_pay * NHIMA_EMPLOYEE_RATE
        employer_contribution = gross_pay * NHIMA_EMPLOYER_RATE
        
        return (round(employee_contribution, 2), round(employer_contribution, 2))
    
    def _calculate_workers_comp(self, gross_pay: float) -> float:
        """
        Calculate Workers Compensation Fund contribution (employer only)
        
        Approximate rate: 1% (varies by industry risk level)
        """
        workers_comp = gross_pay * WORKERS_COMP_RATE
        return round(workers_comp, 2)
    
    def calculate_annual_tax_relief(self, number_of_dependents: int) -> float:
        """
        Calculate annual tax relief for dependents
        (This may be used for annual tax reconciliation)
        """
        # Zambia allows tax relief for dependents - check current rates
        # This is a placeholder - update with actual 2025 rates
        relief_per_dependent = 1000.00  # Annual
        return number_of_dependents * relief_per_dependent


class PayrollService:
    """Service for payroll processing"""
    
    def __init__(self, db: Session):
        self.db = db
        self.payroll_engine = ZambianPayrollEngine(db)
    
    def create_payrun(
        self,
        company_id: str,
        period_start: date,
        period_end: date,
        payment_date: date,
        payrun_name: str = None,
        created_by: str = None
    ) -> models.Payrun:
        """Create a new payrun"""
        # Generate payrun number
        payrun_number = self._generate_payrun_number(company_id, period_start)
        
        payrun = models.Payrun(
            company_id=company_id,
            payrun_number=payrun_number,
            payrun_name=payrun_name or f"Payroll {period_start.strftime('%B %Y')}",
            period_start=period_start,
            period_end=period_end,
            payment_date=payment_date,
            status="draft",
            created_by=created_by
        )
        
        self.db.add(payrun)
        self.db.commit()
        self.db.refresh(payrun)
        
        logger.info(f"Created payrun {payrun_number} for company {company_id}")
        
        return payrun
    
    def calculate_payrun(self, payrun_id: str) -> models.Payrun:
        """Calculate payroll for all employees in the payrun"""
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id
        ).first()
        
        if not payrun:
            raise ValueError("Payrun not found")
        
        if payrun.status != "draft":
            raise ValueError(f"Cannot calculate payrun in status: {payrun.status}")
        
        # Get all active employees
        employees = self.db.query(models.Employee).filter(
            models.Employee.company_id == payrun.company_id,
            models.Employee.employment_status.in_(["active", "probation"]),
            models.Employee.is_active == True
        ).all()
        
        total_gross = 0.0
        total_net = 0.0
        total_paye = 0.0
        total_napsa_employee = 0.0
        total_napsa_employer = 0.0
        total_nhima_employee = 0.0
        total_nhima_employer = 0.0
        
        # Delete existing payslips if recalculating
        self.db.query(models.Payslip).filter(
            models.Payslip.payrun_id == payrun_id
        ).delete()
        
        for employee in employees:
            # Get loan deductions
            loan_deduction = self._calculate_loan_deduction(employee.id, payrun.period_start)
            
            # Calculate payroll
            payroll_data = self.payroll_engine.calculate_employee_payroll(
                employee_id=employee.id,
                period_start=payrun.period_start,
                period_end=payrun.period_end,
                basic_salary=employee.salary_base,
                loan_deductions=loan_deduction
            )
            
            # Create payslip
            payslip = models.Payslip(
                company_id=payrun.company_id,
                payrun_id=payrun_id,
                employee_id=employee.id,
                employee_name=f"{employee.first_name} {employee.last_name}",
                employee_number=employee.employee_no,
                department_name=employee.department.dept_name if employee.department else None,
                position=employee.position,
                basic_salary=payroll_data["earnings"]["basic_salary"],
                earnings_json=payroll_data["earnings"],
                total_earnings=payroll_data["gross_pay"],
                deductions_json={
                    "statutory": payroll_data["statutory_breakdown"]["employee"],
                    "loans": loan_deduction,
                    "other": payroll_data["other_deductions"]
                },
                total_deductions=payroll_data["total_deductions"],
                paye_amount=payroll_data["paye"],
                napsa_employee=payroll_data["napsa_employee"],
                napsa_employer=payroll_data["napsa_employer"],
                nhima_employee=payroll_data["nhima_employee"],
                nhima_employer=payroll_data["nhima_employer"],
                gross_pay=payroll_data["gross_pay"],
                taxable_income=payroll_data["taxable_income"],
                net_pay=payroll_data["net_pay"],
                employer_cost=payroll_data["total_employer_cost"],
                bank_account_number=employee.bank_account,
                bank_name=employee.bank_name,
                mobile_money_number=employee.mobile_money_number,
                status="draft"
            )
            
            self.db.add(payslip)
            
            # Aggregate totals
            total_gross += payroll_data["gross_pay"]
            total_net += payroll_data["net_pay"]
            total_paye += payroll_data["paye"]
            total_napsa_employee += payroll_data["napsa_employee"]
            total_napsa_employer += payroll_data["napsa_employer"]
            total_nhima_employee += payroll_data["nhima_employee"]
            total_nhima_employer += payroll_data["nhima_employer"]
        
        # Update payrun totals
        payrun.total_gross = total_gross
        payrun.total_net = total_net
        payrun.total_deductions = total_gross - total_net
        payrun.total_paye = total_paye
        payrun.total_napsa_employee = total_napsa_employee
        payrun.total_napsa_employer = total_napsa_employer
        payrun.total_nhima_employee = total_nhima_employee
        payrun.total_nhima_employer = total_nhima_employer
        payrun.total_employer_cost = total_gross + total_napsa_employer + total_nhima_employer
        
        self.db.commit()
        self.db.refresh(payrun)
        
        logger.info(f"Calculated payrun {payrun.payrun_number}: {len(employees)} employees, gross {total_gross}, net {total_net}")
        
        return payrun
    
    def _calculate_loan_deduction(self, employee_id: str, period_date: date) -> float:
        """Calculate total loan deductions for an employee"""
        active_loans = self.db.query(models.EmployeeLoan).filter(
            models.EmployeeLoan.employee_id == employee_id,
            models.EmployeeLoan.status == "active",
            models.EmployeeLoan.repayment_start_date <= period_date,
            models.EmployeeLoan.outstanding_balance > 0
        ).all()
        
        total_deduction = sum(loan.repayment_amount for loan in active_loans)
        return total_deduction
    
    def _generate_payrun_number(self, company_id: str, period_start: date) -> str:
        """Generate unique payrun number"""
        year_month = period_start.strftime("%Y%m")
        
        # Get last payrun for this month
        last_payrun = self.db.query(models.Payrun).filter(
            models.Payrun.company_id == company_id,
            models.Payrun.payrun_number.like(f"PR-{year_month}%")
        ).order_by(models.Payrun.created_at.desc()).first()
        
        if last_payrun:
            try:
                last_seq = int(last_payrun.payrun_number.split('-')[-1])
                new_seq = last_seq + 1
            except (IndexError, ValueError):
                new_seq = 1
        else:
            new_seq = 1
        
        return f"PR-{year_month}-{new_seq:03d}"

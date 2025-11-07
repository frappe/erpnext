"""
Statutory Compliance Export Service

Generates export files for Zambian statutory bodies:
- NAPSA (National Pension Scheme Authority)
- NHIMA (National Health Insurance Management Authority)
- PAYE (Pay As You Earn - ZRA)

Formats: CSV, XML, Excel
"""

from datetime import datetime, date
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException
import models
import csv
import io


class StatutoryExportService:
    """Generates statutory compliance export files"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # NAPSA EXPORTS
    # ========================================================================
    
    def generate_napsa_export(
        self,
        company_id: str,
        payrun_id: str,
        format: str = "csv"
    ) -> Dict:
        """
        Generate NAPSA contribution report
        
        NAPSA requires:
        - Employee TPIN
        - Employee Name
        - NRC Number
        - Basic Salary
        - Employee Contribution (5%)
        - Employer Contribution (5%)
        - Total Contribution (10%)
        """
        
        # Get payrun
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id,
            models.Payrun.company_id == company_id
        ).first()
        
        if not payrun:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        # Get company
        company = self.db.query(models.Company).filter(
            models.Company.id == company_id
        ).first()
        
        # Get payslips
        payslips = self.db.query(models.Payslip).filter(
            models.Payslip.payrun_id == payrun_id
        ).all()
        
        # Build NAPSA records
        napsa_records = []
        total_employee = 0.0
        total_employer = 0.0
        
        for payslip in payslips:
            # Get employee details
            employee = self.db.query(models.Employee).filter(
                models.Employee.id == payslip.employee_id
            ).first()
            
            if not employee:
                continue
            
            employee_contribution = payslip.napsa_employee
            employer_contribution = payslip.napsa_employer
            total_contribution = employee_contribution + employer_contribution
            
            total_employee += employee_contribution
            total_employer += employer_contribution
            
            napsa_records.append({
                "tpin": employee.tpin or "NOT_PROVIDED",
                "nrc_number": employee.nrc_number or "NOT_PROVIDED",
                "employee_number": payslip.employee_number,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "full_name": payslip.employee_name,
                "basic_salary": payslip.basic_salary,
                "employee_contribution": employee_contribution,
                "employer_contribution": employer_contribution,
                "total_contribution": total_contribution
            })
        
        # Generate CSV
        if format == "csv":
            csv_content = self._generate_napsa_csv(
                company=company,
                payrun=payrun,
                records=napsa_records,
                total_employee=total_employee,
                total_employer=total_employer
            )
            
            return {
                "success": True,
                "format": "csv",
                "filename": f"NAPSA_{payrun.payrun_number}_{payrun.period_end.strftime('%Y%m%d')}.csv",
                "content": csv_content,
                "summary": {
                    "total_employees": len(napsa_records),
                    "total_employee_contribution": total_employee,
                    "total_employer_contribution": total_employer,
                    "total_contribution": total_employee + total_employer
                }
            }
        
        return {
            "success": True,
            "format": format,
            "records": napsa_records,
            "summary": {
                "total_employees": len(napsa_records),
                "total_employee_contribution": total_employee,
                "total_employer_contribution": total_employer,
                "total_contribution": total_employee + total_employer
            }
        }
    
    def _generate_napsa_csv(
        self,
        company: models.Company,
        payrun: models.Payrun,
        records: List[Dict],
        total_employee: float,
        total_employer: float
    ) -> str:
        """Generate NAPSA CSV format"""
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header section
        writer.writerow(["NAPSA CONTRIBUTIONS RETURN"])
        writer.writerow([""])
        writer.writerow(["Employer Name:", company.name])
        writer.writerow(["TPIN:", company.tpin or "NOT_PROVIDED"])
        writer.writerow(["Period:", f"{payrun.period_start.strftime('%Y-%m-%d')} to {payrun.period_end.strftime('%Y-%m-%d')}"])
        writer.writerow(["Payment Date:", payrun.payment_date.strftime('%Y-%m-%d')])
        writer.writerow([""])
        
        # Column headers
        writer.writerow([
            "TPIN",
            "NRC Number",
            "Employee Number",
            "First Name",
            "Last Name",
            "Basic Salary",
            "Employee Contribution (5%)",
            "Employer Contribution (5%)",
            "Total Contribution"
        ])
        
        # Employee records
        for record in records:
            writer.writerow([
                record["tpin"],
                record["nrc_number"],
                record["employee_number"],
                record["first_name"],
                record["last_name"],
                f"{record['basic_salary']:.2f}",
                f"{record['employee_contribution']:.2f}",
                f"{record['employer_contribution']:.2f}",
                f"{record['total_contribution']:.2f}"
            ])
        
        # Totals
        writer.writerow([""])
        writer.writerow([
            "", "", "", "", "TOTALS:",
            "",
            f"{total_employee:.2f}",
            f"{total_employer:.2f}",
            f"{(total_employee + total_employer):.2f}"
        ])
        
        return output.getvalue()
    
    # ========================================================================
    # NHIMA EXPORTS
    # ========================================================================
    
    def generate_nhima_export(
        self,
        company_id: str,
        payrun_id: str,
        format: str = "csv"
    ) -> Dict:
        """
        Generate NHIMA contribution report
        
        NHIMA requires:
        - Employee TPIN
        - Employee Name
        - NRC Number
        - Basic Salary
        - Employee Contribution (1%)
        - Employer Contribution (1%)
        - Total Contribution (2%)
        """
        
        # Get payrun
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id,
            models.Payrun.company_id == company_id
        ).first()
        
        if not payrun:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        # Get company
        company = self.db.query(models.Company).filter(
            models.Company.id == company_id
        ).first()
        
        # Get payslips
        payslips = self.db.query(models.Payslip).filter(
            models.Payslip.payrun_id == payrun_id
        ).all()
        
        # Build NHIMA records
        nhima_records = []
        total_employee = 0.0
        total_employer = 0.0
        
        for payslip in payslips:
            # Get employee details
            employee = self.db.query(models.Employee).filter(
                models.Employee.id == payslip.employee_id
            ).first()
            
            if not employee:
                continue
            
            employee_contribution = payslip.nhima_employee
            employer_contribution = payslip.nhima_employer
            total_contribution = employee_contribution + employer_contribution
            
            total_employee += employee_contribution
            total_employer += employer_contribution
            
            nhima_records.append({
                "tpin": employee.tpin or "NOT_PROVIDED",
                "nrc_number": employee.nrc_number or "NOT_PROVIDED",
                "employee_number": payslip.employee_number,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "full_name": payslip.employee_name,
                "basic_salary": payslip.basic_salary,
                "employee_contribution": employee_contribution,
                "employer_contribution": employer_contribution,
                "total_contribution": total_contribution
            })
        
        # Generate CSV
        if format == "csv":
            csv_content = self._generate_nhima_csv(
                company=company,
                payrun=payrun,
                records=nhima_records,
                total_employee=total_employee,
                total_employer=total_employer
            )
            
            return {
                "success": True,
                "format": "csv",
                "filename": f"NHIMA_{payrun.payrun_number}_{payrun.period_end.strftime('%Y%m%d')}.csv",
                "content": csv_content,
                "summary": {
                    "total_employees": len(nhima_records),
                    "total_employee_contribution": total_employee,
                    "total_employer_contribution": total_employer,
                    "total_contribution": total_employee + total_employer
                }
            }
        
        return {
            "success": True,
            "format": format,
            "records": nhima_records,
            "summary": {
                "total_employees": len(nhima_records),
                "total_employee_contribution": total_employee,
                "total_employer_contribution": total_employer,
                "total_contribution": total_employee + total_employer
            }
        }
    
    def _generate_nhima_csv(
        self,
        company: models.Company,
        payrun: models.Payrun,
        records: List[Dict],
        total_employee: float,
        total_employer: float
    ) -> str:
        """Generate NHIMA CSV format"""
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header section
        writer.writerow(["NHIMA CONTRIBUTIONS RETURN"])
        writer.writerow([""])
        writer.writerow(["Employer Name:", company.name])
        writer.writerow(["TPIN:", company.tpin or "NOT_PROVIDED"])
        writer.writerow(["Period:", f"{payrun.period_start.strftime('%Y-%m-%d')} to {payrun.period_end.strftime('%Y-%m-%d')}"])
        writer.writerow(["Payment Date:", payrun.payment_date.strftime('%Y-%m-%d')])
        writer.writerow([""])
        
        # Column headers
        writer.writerow([
            "TPIN",
            "NRC Number",
            "Employee Number",
            "First Name",
            "Last Name",
            "Basic Salary",
            "Employee Contribution (1%)",
            "Employer Contribution (1%)",
            "Total Contribution"
        ])
        
        # Employee records
        for record in records:
            writer.writerow([
                record["tpin"],
                record["nrc_number"],
                record["employee_number"],
                record["first_name"],
                record["last_name"],
                f"{record['basic_salary']:.2f}",
                f"{record['employee_contribution']:.2f}",
                f"{record['employer_contribution']:.2f}",
                f"{record['total_contribution']:.2f}"
            ])
        
        # Totals
        writer.writerow([""])
        writer.writerow([
            "", "", "", "", "TOTALS:",
            "",
            f"{total_employee:.2f}",
            f"{total_employer:.2f}",
            f"{(total_employee + total_employer):.2f}"
        ])
        
        return output.getvalue()
    
    # ========================================================================
    # PAYE EXPORTS (ZRA)
    # ========================================================================
    
    def generate_paye_export(
        self,
        company_id: str,
        payrun_id: str,
        format: str = "csv"
    ) -> Dict:
        """
        Generate PAYE (Pay As You Earn) report for ZRA
        
        PAYE requires:
        - Employee TPIN
        - Employee Name
        - Gross Income
        - Taxable Income
        - Tax Deducted (PAYE)
        """
        
        # Get payrun
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id,
            models.Payrun.company_id == company_id
        ).first()
        
        if not payrun:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        # Get company
        company = self.db.query(models.Company).filter(
            models.Company.id == company_id
        ).first()
        
        # Get payslips
        payslips = self.db.query(models.Payslip).filter(
            models.Payslip.payrun_id == payrun_id
        ).all()
        
        # Build PAYE records
        paye_records = []
        total_gross = 0.0
        total_paye = 0.0
        
        for payslip in payslips:
            # Get employee details
            employee = self.db.query(models.Employee).filter(
                models.Employee.id == payslip.employee_id
            ).first()
            
            if not employee:
                continue
            
            gross_income = payslip.total_earnings
            paye_amount = payslip.paye
            
            total_gross += gross_income
            total_paye += paye_amount
            
            paye_records.append({
                "tpin": employee.tpin or "NOT_PROVIDED",
                "nrc_number": employee.nrc_number or "NOT_PROVIDED",
                "employee_number": payslip.employee_number,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "full_name": payslip.employee_name,
                "gross_income": gross_income,
                "taxable_income": gross_income,  # Simplified - should subtract non-taxable allowances
                "paye_deducted": paye_amount
            })
        
        # Generate CSV
        if format == "csv":
            csv_content = self._generate_paye_csv(
                company=company,
                payrun=payrun,
                records=paye_records,
                total_gross=total_gross,
                total_paye=total_paye
            )
            
            return {
                "success": True,
                "format": "csv",
                "filename": f"PAYE_ZRA_{payrun.payrun_number}_{payrun.period_end.strftime('%Y%m%d')}.csv",
                "content": csv_content,
                "summary": {
                    "total_employees": len(paye_records),
                    "total_gross_income": total_gross,
                    "total_paye": total_paye
                }
            }
        
        return {
            "success": True,
            "format": format,
            "records": paye_records,
            "summary": {
                "total_employees": len(paye_records),
                "total_gross_income": total_gross,
                "total_paye": total_paye
            }
        }
    
    def _generate_paye_csv(
        self,
        company: models.Company,
        payrun: models.Payrun,
        records: List[Dict],
        total_gross: float,
        total_paye: float
    ) -> str:
        """Generate PAYE CSV format for ZRA"""
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header section
        writer.writerow(["PAYE RETURN - ZAMBIA REVENUE AUTHORITY"])
        writer.writerow([""])
        writer.writerow(["Employer Name:", company.name])
        writer.writerow(["Employer TPIN:", company.tpin or "NOT_PROVIDED"])
        writer.writerow(["Tax Period:", f"{payrun.period_start.strftime('%B %Y')}"])
        writer.writerow(["Period:", f"{payrun.period_start.strftime('%Y-%m-%d')} to {payrun.period_end.strftime('%Y-%m-%d')}"])
        writer.writerow(["Payment Date:", payrun.payment_date.strftime('%Y-%m-%d')])
        writer.writerow([""])
        
        # Column headers
        writer.writerow([
            "Employee TPIN",
            "NRC Number",
            "Employee Number",
            "First Name",
            "Last Name",
            "Gross Income",
            "Taxable Income",
            "PAYE Deducted"
        ])
        
        # Employee records
        for record in records:
            writer.writerow([
                record["tpin"],
                record["nrc_number"],
                record["employee_number"],
                record["first_name"],
                record["last_name"],
                f"{record['gross_income']:.2f}",
                f"{record['taxable_income']:.2f}",
                f"{record['paye_deducted']:.2f}"
            ])
        
        # Totals
        writer.writerow([""])
        writer.writerow([
            "", "", "", "", "TOTALS:",
            f"{total_gross:.2f}",
            f"{total_gross:.2f}",
            f"{total_paye:.2f}"
        ])
        
        # Footer
        writer.writerow([""])
        writer.writerow(["Generated by ERIK ERP on:", datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        
        return output.getvalue()
    
    # ========================================================================
    # COMBINED STATUTORY REPORT
    # ========================================================================
    
    def generate_combined_statutory_report(
        self,
        company_id: str,
        payrun_id: str
    ) -> Dict:
        """Generate combined statutory report with all contributions"""
        
        napsa = self.generate_napsa_export(company_id, payrun_id, format="json")
        nhima = self.generate_nhima_export(company_id, payrun_id, format="json")
        paye = self.generate_paye_export(company_id, payrun_id, format="json")
        
        return {
            "success": True,
            "payrun_id": payrun_id,
            "napsa": napsa,
            "nhima": nhima,
            "paye": paye,
            "combined_summary": {
                "total_napsa": napsa["summary"]["total_contribution"],
                "total_nhima": nhima["summary"]["total_contribution"],
                "total_paye": paye["summary"]["total_paye"],
                "total_statutory_payment": (
                    napsa["summary"]["total_contribution"] +
                    nhima["summary"]["total_contribution"] +
                    paye["summary"]["total_paye"]
                )
            }
        }

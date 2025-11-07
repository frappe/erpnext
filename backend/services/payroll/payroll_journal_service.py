"""
Payroll Journal Posting Service

Handles:
- Auto-creation of GL journal entries from payroll
- Bank payment file generation
- Payroll to GL reconciliation
- Statutory payment tracking
"""

from datetime import datetime, date
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
import csv
import io
import os


class PayrollJournalService:
    """Manages payroll to GL posting and bank file generation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # GL JOURNAL POSTING
    # ========================================================================
    
    def post_payroll_to_gl(
        self,
        company_id: str,
        payrun_id: str,
        posted_by: str,
        account_mapping: Optional[Dict] = None
    ) -> Dict:
        """
        Post payroll run to general ledger
        Creates journal entry with proper debit/credit allocations
        """
        
        # Get payroll run
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id,
            models.Payrun.company_id == company_id
        ).first()
        
        if not payrun:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        if payrun.status != "posted":
            raise HTTPException(
                status_code=400,
                detail="Payroll must be approved before posting to GL"
            )
        
        if payrun.posted_to_gl:
            raise HTTPException(
                status_code=400,
                detail="Payroll already posted to GL"
            )
        
        # Get or create default account mapping
        if not account_mapping:
            account_mapping = self._get_default_account_mapping(company_id)
        
        # Validate account mapping
        required_accounts = [
            "salary_expense",
            "bank_payable",
            "paye_payable",
            "napsa_employee_payable",
            "napsa_employer_expense",
            "napsa_payable",
            "nhima_employee_payable",
            "nhima_employer_expense",
            "nhima_payable"
        ]
        
        missing_accounts = [acc for acc in required_accounts if acc not in account_mapping]
        if missing_accounts:
            raise HTTPException(
                status_code=400,
                detail=f"Missing account mappings: {', '.join(missing_accounts)}"
            )
        
        # Generate journal number
        journal_number = self._generate_journal_number(company_id, payrun)
        
        # Create journal entry lines
        lines = []
        
        # 1. Debit: Salary Expense
        lines.append({
            "account_id": account_mapping["salary_expense"],
            "description": f"Salary Expense - {payrun.payrun_name}",
            "debit": payrun.total_gross,
            "credit": 0.0
        })
        
        # 2. Debit: NAPSA Employer Contribution
        if payrun.total_napsa_employer > 0:
            lines.append({
                "account_id": account_mapping["napsa_employer_expense"],
                "description": f"NAPSA Employer Contribution - {payrun.payrun_name}",
                "debit": payrun.total_napsa_employer,
                "credit": 0.0
            })
        
        # 3. Debit: NHIMA Employer Contribution
        if payrun.total_nhima_employer > 0:
            lines.append({
                "account_id": account_mapping["nhima_employer_expense"],
                "description": f"NHIMA Employer Contribution - {payrun.payrun_name}",
                "debit": payrun.total_nhima_employer,
                "credit": 0.0
            })
        
        # 4. Credit: Bank Payable (Net Salaries)
        lines.append({
            "account_id": account_mapping["bank_payable"],
            "description": f"Salaries Payable - {payrun.payrun_name}",
            "debit": 0.0,
            "credit": payrun.total_net
        })
        
        # 5. Credit: PAYE Payable
        if payrun.total_paye > 0:
            lines.append({
                "account_id": account_mapping["paye_payable"],
                "description": f"PAYE Payable - {payrun.payrun_name}",
                "debit": 0.0,
                "credit": payrun.total_paye
            })
        
        # 6. Credit: NAPSA Payable (Employee + Employer)
        total_napsa = payrun.total_napsa_employee + payrun.total_napsa_employer
        if total_napsa > 0:
            lines.append({
                "account_id": account_mapping["napsa_payable"],
                "description": f"NAPSA Payable - {payrun.payrun_name}",
                "debit": 0.0,
                "credit": total_napsa
            })
        
        # 7. Credit: NHIMA Payable (Employee + Employer)
        total_nhima = payrun.total_nhima_employee + payrun.total_nhima_employer
        if total_nhima > 0:
            lines.append({
                "account_id": account_mapping["nhima_payable"],
                "description": f"NHIMA Payable - {payrun.payrun_name}",
                "debit": 0.0,
                "credit": total_nhima
            })
        
        # Create journal entry
        journal_entry = models.JournalEntry(
            company_id=company_id,
            journal_number=journal_number,
            entry_date=payrun.payment_date,
            description=f"Payroll Posting - {payrun.payrun_name}",
            currency=payrun.currency,
            exchange_rate=payrun.exchange_rate,
            total_debit=sum(line["debit"] for line in lines),
            total_credit=sum(line["credit"] for line in lines),
            status="draft",
            source_type="payroll",
            source_id=payrun_id,
            created_by=posted_by
        )
        
        self.db.add(journal_entry)
        self.db.flush()
        
        # Create journal entry lines
        for line in lines:
            je_line = models.JournalEntryLine(
                journal_entry_id=journal_entry.id,
                account_id=line["account_id"],
                description=line["description"],
                debit=line["debit"],
                credit=line["credit"]
            )
            self.db.add(je_line)
        
        # Auto-post the journal entry
        journal_entry.status = "posted"
        journal_entry.posted_at = datetime.utcnow()
        journal_entry.posted_by = posted_by
        
        # Update payrun
        payrun.posted_to_gl = True
        payrun.gl_journal_id = journal_entry.id
        
        self.db.commit()
        self.db.refresh(journal_entry)
        
        return {
            "success": True,
            "message": "Payroll posted to GL successfully",
            "journal_entry": {
                "id": journal_entry.id,
                "journal_number": journal_entry.journal_number,
                "entry_date": journal_entry.entry_date.isoformat(),
                "total_debit": journal_entry.total_debit,
                "total_credit": journal_entry.total_credit,
                "status": journal_entry.status
            }
        }
    
    def _get_default_account_mapping(self, company_id: str) -> Dict:
        """Get or create default payroll account mapping"""
        
        # Try to find existing accounts by code
        account_codes = {
            "salary_expense": "6100",
            "bank_payable": "2100",
            "paye_payable": "2210",
            "napsa_employee_payable": "2220",
            "napsa_employer_expense": "6210",
            "napsa_payable": "2220",
            "nhima_employee_payable": "2230",
            "nhima_employer_expense": "6220",
            "nhima_payable": "2230"
        }
        
        mapping = {}
        
        for key, code in account_codes.items():
            account = self.db.query(models.Account).filter(
                models.Account.company_id == company_id,
                models.Account.account_code == code
            ).first()
            
            if account:
                mapping[key] = account.id
            else:
                # Return empty mapping if accounts don't exist
                # This will trigger the validation error
                pass
        
        if len(mapping) != len(account_codes):
            raise HTTPException(
                status_code=400,
                detail="Payroll accounts not configured. Please set up chart of accounts first."
            )
        
        return mapping
    
    def _generate_journal_number(self, company_id: str, payrun: models.Payrun) -> str:
        """Generate journal number for payroll posting"""
        prefix = f"PAY-{payrun.payrun_number}"
        
        # Check if already exists
        existing = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.company_id == company_id,
            models.JournalEntry.journal_number == prefix
        ).first()
        
        if existing:
            # Add sequence number
            count = self.db.query(models.JournalEntry).filter(
                models.JournalEntry.company_id == company_id,
                models.JournalEntry.journal_number.like(f"{prefix}%")
            ).count()
            return f"{prefix}-{count + 1}"
        
        return prefix
    
    # ========================================================================
    # BANK PAYMENT FILE GENERATION
    # ========================================================================
    
    def generate_bank_payment_file(
        self,
        company_id: str,
        payrun_id: str,
        file_format: str = "csv",
        bank_code: Optional[str] = None
    ) -> Dict:
        """
        Generate bank payment file for salary transfers
        Supports CSV format (can be extended for bank-specific formats)
        """
        
        # Get payroll run
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id,
            models.Payrun.company_id == company_id
        ).first()
        
        if not payrun:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        if payrun.status != "posted":
            raise HTTPException(
                status_code=400,
                detail="Payroll must be approved before generating bank file"
            )
        
        # Get all payslips
        payslips = self.db.query(models.Payslip).filter(
            models.Payslip.payrun_id == payrun_id,
            models.Payslip.status == "approved"
        ).all()
        
        if not payslips:
            raise HTTPException(status_code=400, detail="No approved payslips found")
        
        # Generate file based on format
        if file_format.lower() == "csv":
            file_content = self._generate_csv_payment_file(payrun, payslips, company_id)
            file_extension = "csv"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file_format}"
            )
        
        # Save file path
        file_name = f"payroll_{payrun.payrun_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
        file_path = f"payroll_exports/{file_name}"
        
        # Ensure directory exists
        os.makedirs("payroll_exports", exist_ok=True)
        
        # Write file
        with open(file_path, 'w', newline='') as f:
            f.write(file_content)
        
        # Update payrun
        payrun.bank_file_path = file_path
        payrun.exported_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "Bank payment file generated successfully",
            "file_path": file_path,
            "file_name": file_name,
            "total_amount": payrun.total_net,
            "employee_count": len(payslips),
            "file_content": file_content  # Return content for download
        }
    
    def _generate_csv_payment_file(
        self,
        payrun: models.Payrun,
        payslips: List[models.Payslip],
        company_id: str
    ) -> str:
        """Generate CSV payment file"""
        
        # Get company details
        company = self.db.query(models.Company).filter(
            models.Company.id == company_id
        ).first()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Employee Number",
            "Employee Name",
            "Bank Name",
            "Branch Code",
            "Account Number",
            "Amount",
            "Payment Date",
            "Reference"
        ])
        
        # Get employee banking details and write rows
        for payslip in payslips:
            employee = self.db.query(models.Employee).filter(
                models.Employee.id == payslip.employee_id
            ).first()
            
            if not employee:
                continue
            
            # Get banking details (from employee model)
            bank_name = getattr(employee, 'bank_name', 'N/A')
            branch_code = getattr(employee, 'bank_branch_code', '')
            account_number = getattr(employee, 'bank_account_number', '')
            
            writer.writerow([
                payslip.employee_number,
                payslip.employee_name,
                bank_name,
                branch_code,
                account_number,
                f"{payslip.net_pay:.2f}",
                payrun.payment_date.strftime('%Y-%m-%d'),
                f"{payrun.payrun_number}-{payslip.employee_number}"
            ])
        
        # Summary row
        writer.writerow([])
        writer.writerow([
            "TOTAL",
            f"{len(payslips)} employees",
            "",
            "",
            "",
            f"{sum(ps.net_pay for ps in payslips):.2f}",
            "",
            ""
        ])
        
        return output.getvalue()
    
    # ========================================================================
    # STATUTORY PAYMENT REPORTS
    # ========================================================================
    
    def generate_statutory_payment_summary(
        self,
        company_id: str,
        payrun_id: str
    ) -> Dict:
        """
        Generate summary of statutory payments (PAYE, NAPSA, NHIMA)
        for remittance to authorities
        """
        
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id,
            models.Payrun.company_id == company_id
        ).first()
        
        if not payrun:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        return {
            "success": True,
            "payrun_number": payrun.payrun_number,
            "payrun_name": payrun.payrun_name,
            "period": {
                "start": payrun.period_start.isoformat(),
                "end": payrun.period_end.isoformat(),
                "payment_date": payrun.payment_date.isoformat()
            },
            "statutory_payments": {
                "paye": {
                    "description": "Pay As You Earn (Income Tax)",
                    "amount": payrun.total_paye,
                    "due_date": self._calculate_statutory_due_date(payrun.period_end, "PAYE")
                },
                "napsa": {
                    "description": "National Pension Scheme Authority",
                    "employee_contribution": payrun.total_napsa_employee,
                    "employer_contribution": payrun.total_napsa_employer,
                    "total_amount": payrun.total_napsa_employee + payrun.total_napsa_employer,
                    "due_date": self._calculate_statutory_due_date(payrun.period_end, "NAPSA")
                },
                "nhima": {
                    "description": "National Health Insurance Management Authority",
                    "employee_contribution": payrun.total_nhima_employee,
                    "employer_contribution": payrun.total_nhima_employer,
                    "total_amount": payrun.total_nhima_employee + payrun.total_nhima_employer,
                    "due_date": self._calculate_statutory_due_date(payrun.period_end, "NHIMA")
                }
            },
            "total_statutory_amount": (
                payrun.total_paye +
                payrun.total_napsa_employee +
                payrun.total_napsa_employer +
                payrun.total_nhima_employee +
                payrun.total_nhima_employer
            )
        }
    
    def _calculate_statutory_due_date(self, period_end: date, payment_type: str) -> str:
        """Calculate due date for statutory payments"""
        # Zambian statutory payment deadlines:
        # PAYE, NAPSA, NHIMA: 10th of following month
        
        from dateutil.relativedelta import relativedelta
        
        next_month = period_end + relativedelta(months=1)
        due_date = date(next_month.year, next_month.month, 10)
        
        return due_date.isoformat()
    
    # ========================================================================
    # REVERSAL & CORRECTIONS
    # ========================================================================
    
    def reverse_payroll_posting(
        self,
        company_id: str,
        payrun_id: str,
        reversed_by: str,
        reason: str
    ) -> Dict:
        """Reverse GL posting for payroll (creates reversal journal)"""
        
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payrun_id,
            models.Payrun.company_id == company_id
        ).first()
        
        if not payrun:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        if not payrun.posted_to_gl or not payrun.gl_journal_id:
            raise HTTPException(
                status_code=400,
                detail="Payroll has not been posted to GL"
            )
        
        # Get original journal
        original_journal = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.id == payrun.gl_journal_id
        ).first()
        
        if not original_journal:
            raise HTTPException(status_code=404, detail="Original journal entry not found")
        
        # Create reversal journal
        reversal_number = f"REV-{original_journal.journal_number}"
        
        reversal_journal = models.JournalEntry(
            company_id=company_id,
            journal_number=reversal_number,
            entry_date=date.today(),
            description=f"REVERSAL: {original_journal.description} - Reason: {reason}",
            currency=original_journal.currency,
            exchange_rate=original_journal.exchange_rate,
            total_debit=original_journal.total_credit,  # Swap
            total_credit=original_journal.total_debit,   # Swap
            status="posted",
            source_type="payroll_reversal",
            source_id=payrun_id,
            reversal_of_id=original_journal.id,
            created_by=reversed_by,
            posted_at=datetime.utcnow(),
            posted_by=reversed_by
        )
        
        self.db.add(reversal_journal)
        self.db.flush()
        
        # Create reversal lines (swap debit/credit)
        original_lines = self.db.query(models.JournalEntryLine).filter(
            models.JournalEntryLine.journal_entry_id == original_journal.id
        ).all()
        
        for orig_line in original_lines:
            rev_line = models.JournalEntryLine(
                journal_entry_id=reversal_journal.id,
                account_id=orig_line.account_id,
                description=f"REVERSAL: {orig_line.description}",
                debit=orig_line.credit,   # Swap
                credit=orig_line.debit    # Swap
            )
            self.db.add(rev_line)
        
        # Update payrun
        payrun.posted_to_gl = False
        payrun.gl_journal_id = None
        payrun.status = "validated"  # Back to validated status
        
        self.db.commit()
        self.db.refresh(reversal_journal)
        
        return {
            "success": True,
            "message": "Payroll GL posting reversed successfully",
            "reversal_journal": {
                "id": reversal_journal.id,
                "journal_number": reversal_journal.journal_number,
                "entry_date": reversal_journal.entry_date.isoformat(),
                "total_debit": reversal_journal.total_debit,
                "total_credit": reversal_journal.total_credit
            }
        }

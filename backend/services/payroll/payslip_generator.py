"""
Payslip Generation Service

Handles:
- HTML payslip generation
- Payslip formatting and styling
- Email distribution
- Batch payslip generation
"""

from datetime import datetime, date
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
import base64


class PayslipGenerator:
    """Generates payslips in HTML format"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # PAYSLIP GENERATION
    # ========================================================================
    
    def generate_payslip_html(
        self,
        company_id: str,
        payslip_id: str
    ) -> str:
        """Generate HTML payslip for a single employee"""
        
        # Get payslip
        payslip = self.db.query(models.Payslip).filter(
            models.Payslip.id == payslip_id,
            models.Payslip.company_id == company_id
        ).first()
        
        if not payslip:
            raise HTTPException(status_code=404, detail="Payslip not found")
        
        # Get payrun
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payslip.payrun_id
        ).first()
        
        # Get company
        company = self.db.query(models.Company).filter(
            models.Company.id == company_id
        ).first()
        
        # Get employee
        employee = self.db.query(models.Employee).filter(
            models.Employee.id == payslip.employee_id
        ).first()
        
        # Generate HTML
        html = self._create_payslip_template(payslip, payrun, company, employee)
        
        return html
    
    def _create_payslip_template(
        self,
        payslip: models.Payslip,
        payrun: models.Payrun,
        company: models.Company,
        employee: Optional[models.Employee]
    ) -> str:
        """Create HTML template for payslip"""
        
        # Calculate totals
        earnings_breakdown = payslip.earnings_json or {}
        deductions_breakdown = payslip.deductions_json or {}
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Payslip - {payslip.employee_name}</title>
    <style>
        @media print {{
            .no-print {{ display: none; }}
            body {{ margin: 0; }}
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        
        .payslip-container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        
        .header {{
            text-align: center;
            border-bottom: 3px solid #00D9A3;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .company-name {{
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        
        .payslip-title {{
            font-size: 20px;
            color: #666;
            margin-top: 10px;
        }}
        
        .info-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .info-box {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
        }}
        
        .info-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        
        .info-value {{
            font-size: 16px;
            color: #2c3e50;
            font-weight: 600;
        }}
        
        .breakdown-section {{
            margin-bottom: 30px;
        }}
        
        .section-title {{
            font-size: 18px;
            color: #2c3e50;
            font-weight: bold;
            border-bottom: 2px solid #00D9A3;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }}
        
        .breakdown-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .breakdown-table td {{
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .breakdown-table .label {{
            color: #666;
        }}
        
        .breakdown-table .amount {{
            text-align: right;
            font-weight: 600;
            color: #2c3e50;
        }}
        
        .breakdown-table tr:last-child td {{
            border-bottom: none;
        }}
        
        .totals-section {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-top: 30px;
        }}
        
        .total-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            font-size: 16px;
        }}
        
        .total-row.main {{
            font-size: 20px;
            font-weight: bold;
            color: #00D9A3;
            border-top: 2px solid #00D9A3;
            padding-top: 15px;
            margin-top: 10px;
        }}
        
        .statutory-section {{
            margin-top: 30px;
            padding: 20px;
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 5px;
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
        
        .print-button {{
            background: #00D9A3;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin: 20px auto;
            display: block;
        }}
        
        .print-button:hover {{
            background: #00c090;
        }}
    </style>
</head>
<body>
    <div class="payslip-container">
        <!-- Header -->
        <div class="header">
            <div class="company-name">{company.name if company else 'ERIK ERP'}</div>
            <div class="payslip-title">PAYSLIP</div>
            <div style="margin-top: 10px; color: #666;">
                {payrun.payrun_name if payrun else 'Payroll'}
            </div>
        </div>
        
        <!-- Employee & Period Information -->
        <div class="info-section">
            <div class="info-box">
                <div class="info-label">Employee Name</div>
                <div class="info-value">{payslip.employee_name}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Employee Number</div>
                <div class="info-value">{payslip.employee_number}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Department</div>
                <div class="info-value">{payslip.department_name or 'N/A'}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Position</div>
                <div class="info-value">{payslip.position or 'N/A'}</div>
            </div>
            <div class="info-box">
                <div class="info-label">Pay Period</div>
                <div class="info-value">
                    {payrun.period_start.strftime('%d %b %Y') if payrun else 'N/A'} - 
                    {payrun.period_end.strftime('%d %b %Y') if payrun else 'N/A'}
                </div>
            </div>
            <div class="info-box">
                <div class="info-label">Payment Date</div>
                <div class="info-value">{payrun.payment_date.strftime('%d %b %Y') if payrun else 'N/A'}</div>
            </div>
        </div>
        
        <!-- Earnings Section -->
        <div class="breakdown-section">
            <div class="section-title">EARNINGS</div>
            <table class="breakdown-table">
                <tr>
                    <td class="label">Basic Salary</td>
                    <td class="amount">{payslip.currency} {payslip.basic_salary:,.2f}</td>
                </tr>
                {self._render_earnings_lines(earnings_breakdown)}
                <tr style="font-weight: bold; border-top: 2px solid #00D9A3;">
                    <td class="label">Total Earnings</td>
                    <td class="amount">{payslip.currency} {payslip.total_earnings:,.2f}</td>
                </tr>
            </table>
        </div>
        
        <!-- Deductions Section -->
        <div class="breakdown-section">
            <div class="section-title">DEDUCTIONS</div>
            <table class="breakdown-table">
                <tr>
                    <td class="label">PAYE (Income Tax)</td>
                    <td class="amount">{payslip.currency} {payslip.paye:,.2f}</td>
                </tr>
                <tr>
                    <td class="label">NAPSA (Employee Contribution)</td>
                    <td class="amount">{payslip.currency} {payslip.napsa_employee:,.2f}</td>
                </tr>
                <tr>
                    <td class="label">NHIMA (Employee Contribution)</td>
                    <td class="amount">{payslip.currency} {payslip.nhima_employee:,.2f}</td>
                </tr>
                {self._render_other_deductions(deductions_breakdown)}
                <tr style="font-weight: bold; border-top: 2px solid #dc3545;">
                    <td class="label">Total Deductions</td>
                    <td class="amount">{payslip.currency} {payslip.total_deductions:,.2f}</td>
                </tr>
            </table>
        </div>
        
        <!-- Net Pay Section -->
        <div class="totals-section">
            <div class="total-row">
                <span>Gross Salary:</span>
                <span>{payslip.currency} {payslip.total_earnings:,.2f}</span>
            </div>
            <div class="total-row">
                <span>Total Deductions:</span>
                <span>{payslip.currency} {payslip.total_deductions:,.2f}</span>
            </div>
            <div class="total-row main">
                <span>NET PAY:</span>
                <span>{payslip.currency} {payslip.net_pay:,.2f}</span>
            </div>
        </div>
        
        <!-- Statutory Contributions -->
        <div class="statutory-section">
            <div class="section-title">EMPLOYER CONTRIBUTIONS</div>
            <table class="breakdown-table">
                <tr>
                    <td class="label">NAPSA (Employer Contribution)</td>
                    <td class="amount">{payslip.currency} {payslip.napsa_employer:,.2f}</td>
                </tr>
                <tr>
                    <td class="label">NHIMA (Employer Contribution)</td>
                    <td class="amount">{payslip.currency} {payslip.nhima_employer:,.2f}</td>
                </tr>
            </table>
        </div>
        
        <!-- Attendance Summary -->
        {self._render_attendance_section(payslip)}
        
        <!-- Footer -->
        <div class="footer">
            <p>This is a computer-generated payslip and does not require a signature.</p>
            <p>Generated on {datetime.now().strftime('%d %B %Y at %H:%M')}</p>
            <p style="margin-top: 10px; color: #00D9A3; font-weight: bold;">Powered by ERIK ERP</p>
        </div>
        
        <!-- Print Button (hidden when printing) -->
        <button class="print-button no-print" onclick="window.print()">
            Print / Save as PDF
        </button>
    </div>
</body>
</html>
        """
        
        return html
    
    def _render_earnings_lines(self, earnings_breakdown: Dict) -> str:
        """Render additional earnings lines"""
        if not earnings_breakdown:
            return ""
        
        lines = []
        for key, value in earnings_breakdown.items():
            if key != "basic_salary" and isinstance(value, (int, float)) and value > 0:
                label = key.replace('_', ' ').title()
                lines.append(f"""
                <tr>
                    <td class="label">{label}</td>
                    <td class="amount">ZMW {value:,.2f}</td>
                </tr>
                """)
        
        return "\n".join(lines)
    
    def _render_other_deductions(self, deductions_breakdown: Dict) -> str:
        """Render other deductions (loans, advances, etc.)"""
        if not deductions_breakdown:
            return ""
        
        lines = []
        excluded = ['paye', 'napsa_employee', 'nhima_employee', 'workers_comp_employee']
        
        for key, value in deductions_breakdown.items():
            if key not in excluded:
                if isinstance(value, dict):
                    # Handle loan deductions dictionary
                    for loan_key, loan_value in value.items():
                        if isinstance(loan_value, (int, float)) and loan_value > 0:
                            label = loan_key.replace('_', ' ').title()
                            lines.append(f"""
                            <tr>
                                <td class="label">{label}</td>
                                <td class="amount">ZMW {loan_value:,.2f}</td>
                            </tr>
                            """)
                elif isinstance(value, (int, float)) and value > 0:
                    label = key.replace('_', ' ').title()
                    lines.append(f"""
                    <tr>
                        <td class="label">{label}</td>
                        <td class="amount">ZMW {value:,.2f}</td>
                    </tr>
                    """)
        
        return "\n".join(lines)
    
    def _render_attendance_section(self, payslip: models.Payslip) -> str:
        """Render attendance summary section"""
        if payslip.attendance_days == 0 and payslip.leave_days == 0:
            return ""
        
        return f"""
        <div style="margin-top: 30px; padding: 20px; background: #e3f2fd; border-radius: 5px;">
            <div class="section-title">ATTENDANCE SUMMARY</div>
            <table class="breakdown-table">
                <tr>
                    <td class="label">Days Present</td>
                    <td class="amount">{payslip.attendance_days} days</td>
                </tr>
                <tr>
                    <td class="label">Leave Days</td>
                    <td class="amount">{payslip.leave_days} days</td>
                </tr>
                {f'<tr><td class="label">Unpaid Leave</td><td class="amount">{payslip.unpaid_leave_days} days</td></tr>' if payslip.unpaid_leave_days > 0 else ''}
                {f'<tr><td class="label">Overtime Hours</td><td class="amount">{payslip.overtime_hours} hours</td></tr>' if payslip.overtime_hours > 0 else ''}
            </table>
        </div>
        """
    
    # ========================================================================
    # BATCH GENERATION
    # ========================================================================
    
    def generate_batch_payslips(
        self,
        company_id: str,
        payrun_id: str
    ) -> List[Dict]:
        """Generate payslips for all employees in a payroll run"""
        
        payslips = self.db.query(models.Payslip).filter(
            models.Payslip.company_id == company_id,
            models.Payslip.payrun_id == payrun_id
        ).all()
        
        if not payslips:
            raise HTTPException(status_code=404, detail="No payslips found for this payroll run")
        
        results = []
        for payslip in payslips:
            try:
                html = self.generate_payslip_html(company_id, payslip.id)
                results.append({
                    "payslip_id": payslip.id,
                    "employee_id": payslip.employee_id,
                    "employee_name": payslip.employee_name,
                    "employee_number": payslip.employee_number,
                    "success": True,
                    "html": html
                })
            except Exception as e:
                results.append({
                    "payslip_id": payslip.id,
                    "employee_id": payslip.employee_id,
                    "employee_name": payslip.employee_name,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    # ========================================================================
    # EMAIL DISTRIBUTION
    # ========================================================================
    
    def send_payslip_email(
        self,
        company_id: str,
        payslip_id: str,
        recipient_email: Optional[str] = None
    ) -> Dict:
        """Send payslip via email"""
        
        # Get payslip
        payslip = self.db.query(models.Payslip).filter(
            models.Payslip.id == payslip_id,
            models.Payslip.company_id == company_id
        ).first()
        
        if not payslip:
            raise HTTPException(status_code=404, detail="Payslip not found")
        
        # Get employee email if not provided
        if not recipient_email:
            employee = self.db.query(models.Employee).filter(
                models.Employee.id == payslip.employee_id
            ).first()
            
            if not employee or not employee.email:
                raise HTTPException(
                    status_code=400,
                    detail="Employee email not found"
                )
            
            recipient_email = employee.email
        
        # Generate HTML payslip
        html = self.generate_payslip_html(company_id, payslip_id)
        
        # Get payrun for subject line
        payrun = self.db.query(models.Payrun).filter(
            models.Payrun.id == payslip.payrun_id
        ).first()
        
        # TODO: Implement actual email sending via notification service
        # For now, return success with email details
        
        return {
            "success": True,
            "message": f"Payslip email prepared for {recipient_email}",
            "recipient": recipient_email,
            "subject": f"Payslip - {payrun.payrun_name if payrun else 'Payroll'}",
            "html_content": html,
            "note": "Email sending requires SMTP configuration"
        }
    
    def send_batch_payslip_emails(
        self,
        company_id: str,
        payrun_id: str
    ) -> Dict:
        """Send payslips to all employees via email"""
        
        payslips = self.db.query(models.Payslip).filter(
            models.Payslip.company_id == company_id,
            models.Payslip.payrun_id == payrun_id,
            models.Payslip.status == "approved"
        ).all()
        
        if not payslips:
            raise HTTPException(status_code=404, detail="No approved payslips found")
        
        sent = 0
        failed = 0
        errors = []
        
        for payslip in payslips:
            try:
                # Get employee email
                employee = self.db.query(models.Employee).filter(
                    models.Employee.id == payslip.employee_id
                ).first()
                
                if employee and employee.email:
                    self.send_payslip_email(company_id, payslip.id, employee.email)
                    sent += 1
                else:
                    failed += 1
                    errors.append({
                        "employee_name": payslip.employee_name,
                        "error": "No email address"
                    })
            except Exception as e:
                failed += 1
                errors.append({
                    "employee_name": payslip.employee_name,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "total": len(payslips),
            "sent": sent,
            "failed": failed,
            "errors": errors if errors else None
        }

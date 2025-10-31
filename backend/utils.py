from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
import models

def calculate_paye_zambia(taxable_income: float) -> float:
    """
    Calculate PAYE tax based on Zambian tax brackets (2025)
    Tax-free threshold: K4,500 per month
    """
    annual_income = taxable_income * 12
    annual_threshold = 54000
    
    if annual_income <= annual_threshold:
        return 0.0
    
    taxable = annual_income - annual_threshold
    
    if taxable <= 57600:
        monthly_tax = (taxable * 0.25) / 12
    elif taxable <= 122400:
        monthly_tax = ((57600 * 0.25) + ((taxable - 57600) * 0.30)) / 12
    else:
        monthly_tax = ((57600 * 0.25) + (64800 * 0.30) + ((taxable - 122400) * 0.37)) / 12
    
    return round(monthly_tax, 2)

def calculate_napsa(gross_salary: float) -> tuple:
    """
    Calculate NAPSA contributions
    Employee: 5% of gross salary
    Employer: 5% of gross salary
    """
    employee = round(gross_salary * 0.05, 2)
    employer = round(gross_salary * 0.05, 2)
    return employee, employer

def calculate_nhima(gross_salary: float) -> tuple:
    """
    Calculate NHIMA contributions
    Employee: 1% of gross salary
    Employer: 1% of gross salary
    """
    employee = round(gross_salary * 0.01, 2)
    employer = round(gross_salary * 0.01, 2)
    return employee, employer

def generate_payslip_data(employee: models.Employee, period_month: int, period_year: int) -> dict:
    """Generate complete payslip data with all calculations"""
    basic_salary = employee.salary_base
    gross_salary = basic_salary
    
    napsa_employee, napsa_employer = calculate_napsa(gross_salary)
    nhima_employee, nhima_employer = calculate_nhima(gross_salary)
    
    taxable_income = gross_salary - napsa_employee
    paye_tax = calculate_paye_zambia(taxable_income)
    
    total_deductions = paye_tax + napsa_employee + nhima_employee
    net_salary = gross_salary - total_deductions
    
    return {
        "basic_salary": basic_salary,
        "gross_salary": gross_salary,
        "paye_tax": paye_tax,
        "napsa_employee": napsa_employee,
        "napsa_employer": napsa_employer,
        "nhima_employee": nhima_employee,
        "nhima_employer": nhima_employer,
        "total_deductions": total_deductions,
        "net_salary": net_salary,
        "period_month": period_month,
        "period_year": period_year
    }

def get_account_balance(db: Session, company_id: str, account_id: str, start_date: date, end_date: date) -> float:
    """Calculate account balance from journal lines within date range"""
    debits = db.query(func.sum(models.JournalLine.amount)).join(
        models.JournalEntry
    ).filter(
        models.JournalLine.account_id == account_id,
        models.JournalLine.side == "debit",
        models.JournalEntry.company_id == company_id,
        models.JournalEntry.date >= start_date,
        models.JournalEntry.date <= end_date
    ).scalar() or 0.0
    
    credits = db.query(func.sum(models.JournalLine.amount)).join(
        models.JournalEntry
    ).filter(
        models.JournalLine.account_id == account_id,
        models.JournalLine.side == "credit",
        models.JournalEntry.company_id == company_id,
        models.JournalEntry.date >= start_date,
        models.JournalEntry.date <= end_date
    ).scalar() or 0.0
    
    return debits - credits

def generate_income_statement(db: Session, company_id: str, start_date: date, end_date: date) -> dict:
    """Generate Profit & Loss Statement"""
    revenue_accounts = db.query(models.Account).filter(
        models.Account.company_id == company_id,
        models.Account.account_type == "revenue"
    ).all()
    
    expense_accounts = db.query(models.Account).filter(
        models.Account.company_id == company_id,
        models.Account.account_type == "expense"
    ).all()
    
    total_revenue = 0.0
    revenue_details = []
    for account in revenue_accounts:
        balance = abs(get_account_balance(db, company_id, account.id, start_date, end_date))
        if balance != 0:
            total_revenue += balance
            revenue_details.append({
                "code": account.code,
                "name": account.name,
                "amount": balance
            })
    
    total_expenses = 0.0
    expense_details = []
    for account in expense_accounts:
        balance = abs(get_account_balance(db, company_id, account.id, start_date, end_date))
        if balance != 0:
            total_expenses += balance
            expense_details.append({
                "code": account.code,
                "name": account.name,
                "amount": balance
            })
    
    net_income = total_revenue - total_expenses
    
    return {
        "report_type": "Income Statement",
        "period": f"{start_date} to {end_date}",
        "sections": {
            "revenue": {
                "title": "Revenue",
                "items": revenue_details,
                "total": total_revenue
            },
            "expenses": {
                "title": "Expenses",
                "items": expense_details,
                "total": total_expenses
            },
            "net_income": net_income
        }
    }

def generate_balance_sheet(db: Session, company_id: str, as_of_date: date) -> dict:
    """Generate Balance Sheet"""
    start_date = date(2000, 1, 1)
    
    asset_accounts = db.query(models.Account).filter(
        models.Account.company_id == company_id,
        models.Account.account_type == "asset"
    ).all()
    
    liability_accounts = db.query(models.Account).filter(
        models.Account.company_id == company_id,
        models.Account.account_type == "liability"
    ).all()
    
    equity_accounts = db.query(models.Account).filter(
        models.Account.company_id == company_id,
        models.Account.account_type == "equity"
    ).all()
    
    total_assets = 0.0
    asset_details = []
    for account in asset_accounts:
        balance = get_account_balance(db, company_id, account.id, start_date, as_of_date)
        if balance != 0:
            total_assets += abs(balance)
            asset_details.append({
                "code": account.code,
                "name": account.name,
                "amount": abs(balance)
            })
    
    total_liabilities = 0.0
    liability_details = []
    for account in liability_accounts:
        balance = get_account_balance(db, company_id, account.id, start_date, as_of_date)
        if balance != 0:
            total_liabilities += abs(balance)
            liability_details.append({
                "code": account.code,
                "name": account.name,
                "amount": abs(balance)
            })
    
    total_equity = 0.0
    equity_details = []
    for account in equity_accounts:
        balance = get_account_balance(db, company_id, account.id, start_date, as_of_date)
        if balance != 0:
            total_equity += abs(balance)
            equity_details.append({
                "code": account.code,
                "name": account.name,
                "amount": abs(balance)
            })
    
    return {
        "report_type": "Balance Sheet",
        "period": f"As of {as_of_date}",
        "sections": {
            "assets": {
                "title": "Assets",
                "items": asset_details,
                "total": total_assets
            },
            "liabilities": {
                "title": "Liabilities",
                "items": liability_details,
                "total": total_liabilities
            },
            "equity": {
                "title": "Equity",
                "items": equity_details,
                "total": total_equity
            },
            "total_liabilities_equity": total_liabilities + total_equity
        }
    }

def generate_cash_flow(db: Session, company_id: str, start_date: date, end_date: date) -> dict:
    """Generate Cash Flow Statement"""
    asset_accounts = db.query(models.Account).filter(
        models.Account.company_id == company_id,
        models.Account.account_type == "asset"
    ).all()
    
    liability_accounts = db.query(models.Account).filter(
        models.Account.company_id == company_id,
        models.Account.account_type == "liability"
    ).all()
    
    revenue_accounts = db.query(models.Account).filter(
        models.Account.company_id == company_id,
        models.Account.account_type == "revenue"
    ).all()
    
    expense_accounts = db.query(models.Account).filter(
        models.Account.company_id == company_id,
        models.Account.account_type == "expense"
    ).all()
    
    total_revenue = sum(abs(get_account_balance(db, company_id, acc.id, start_date, end_date)) for acc in revenue_accounts)
    total_expenses = sum(abs(get_account_balance(db, company_id, acc.id, start_date, end_date)) for acc in expense_accounts)
    
    cash_from_operations = total_revenue - total_expenses
    
    investing_items = []
    total_investing = 0.0
    for account in asset_accounts:
        if "Cash" not in account.name and "Bank" not in account.name:
            balance = get_account_balance(db, company_id, account.id, start_date, end_date)
            if balance != 0:
                total_investing += balance
                investing_items.append({
                    "code": account.code,
                    "name": account.name,
                    "amount": balance
                })
    
    financing_items = []
    total_financing = 0.0
    for account in liability_accounts:
        balance = get_account_balance(db, company_id, account.id, start_date, end_date)
        if balance != 0:
            total_financing += balance
            financing_items.append({
                "code": account.code,
                "name": account.name,
                "amount": balance
            })
    
    net_cash_change = cash_from_operations + total_investing + total_financing
    
    return {
        "report_type": "Cash Flow Statement",
        "period": f"{start_date} to {end_date}",
        "sections": {
            "operating": {
                "title": "Cash from Operating Activities",
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
                "total": cash_from_operations
            },
            "investing": {
                "title": "Cash from Investing Activities",
                "items": investing_items,
                "total": total_investing
            },
            "financing": {
                "title": "Cash from Financing Activities",
                "items": financing_items,
                "total": total_financing
            },
            "net_change": net_cash_change
        }
    }

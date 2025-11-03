"""
Sample Data Generator for ERIK ERP

Generates comprehensive test data for demonstration:
- Companies
- Employees with Zambian compliance data
- Statutory obligations
- Payruns and payslips
- Chart of accounts
- Journal entries
- Invoices
"""

import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
import random

from database import SessionLocal
import models
from auth import get_password_hash
from services.compliance.statutory_compliance import StatutoryComplianceService
from services.payroll.payroll_service import PayrollService


def generate_sample_data():
    """Generate comprehensive sample data for demo"""
    
    db = SessionLocal()
    
    try:
        print("🚀 Starting ERIK ERP Sample Data Generation...")
        print("=" * 60)
        
        print("\n📊 Step 1: Creating Demo Company...")
        company = create_demo_company(db)
        print(f"✓ Created company: {company.name}")
        
        print("\n👤 Step 2: Creating Demo User...")
        user = create_demo_user(db, company.id)
        print(f"✓ Created user: {user.username}")
        
        print("\n👥 Step 3: Creating Employees...")
        employees = create_employees(db, company.id)
        print(f"✓ Created {len(employees)} employees")
        
        print("\n💰 Step 4: Creating Chart of Accounts...")
        accounts = create_chart_of_accounts(db, company.id)
        print(f"✓ Created {len(accounts)} accounts")
        
        print("\n📅 Step 5: Generating Statutory Obligations...")
        obligations = generate_obligations(db, company.id)
        print(f"✓ Generated {len(obligations)} statutory obligations")
        
        print("\n💵 Step 6: Creating Payrun...")
        payrun, payslips = create_payrun(db, company.id, employees, user.id)
        print(f"✓ Created payrun with {len(payslips)} payslips")
        
        print("\n📝 Step 7: Creating Journal Entries...")
        entries = create_journal_entries(db, company.id, accounts, user.id)
        print(f"✓ Created {len(entries)} journal entries")
        
        print("\n" + "=" * 60)
        print("✅ Sample data generation completed successfully!")
        print("\n📋 Summary:")
        print(f"  • Company: {company.name}")
        print(f"  • Login: {user.username} / password: demo123")
        print(f"  • Employees: {len(employees)}")
        print(f"  • Accounts: {len(accounts)}")
        print(f"  • Obligations: {len(obligations)}")
        print(f"  • Payslips: {len(payslips)}")
        print(f"  • Journal Entries: {len(entries)}")
        print("\n🌐 Access the system at http://localhost:5000")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error generating sample data: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def create_demo_company(db):
    """Create demo company"""
    
    existing = db.query(models.Company).filter(
        models.Company.name == "Zambia Demo Corporation"
    ).first()
    
    if existing:
        return existing
    
    company = models.Company(
        name="Zambia Demo Corporation",
        email="demo@erikerp.zm",
        phone="+260977123456",
        address="Plot 123, Independence Avenue",
        city="Lusaka",
        country="Zambia",
        tax_id="1000123456",
        registration_number="119900123456",
        industry="Technology",
        is_active=True
    )
    
    db.add(company)
    db.commit()
    db.refresh(company)
    
    return company


def create_demo_user(db, company_id):
    """Create demo user"""
    
    existing = db.query(models.User).filter(
        models.User.username == "demo@erikerp.zm"
    ).first()
    
    if existing:
        return existing
    
    user = models.User(
        company_id=company_id,
        username="demo@erikerp.zm",
        email="demo@erikerp.zm",
        hashed_password=get_password_hash("demo123"),
        full_name="Demo Administrator",
        role="admin",
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def create_employees(db, company_id):
    """Create sample employees with Zambian compliance data"""
    
    employees_data = [
        {
            "first_name": "John", "last_name": "Banda",
            "email": "john.banda@demo.zm", "phone": "+260977111222",
            "nrc": "123456/10/1", "tpin": "1001234567",
            "napsa_number": "9001234567", "nhima_number": "8001234567",
            "basic_salary": 12000.00, "position": "Software Engineer"
        },
        {
            "first_name": "Mary", "last_name": "Mwansa",
            "email": "mary.mwansa@demo.zm", "phone": "+260966222333",
            "nrc": "234567/11/1", "tpin": "1001234568",
            "napsa_number": "9001234568", "nhima_number": "8001234568",
            "basic_salary": 15000.00, "position": "Senior Developer"
        },
        {
            "first_name": "Peter", "last_name": "Phiri",
            "email": "peter.phiri@demo.zm", "phone": "+260955333444",
            "nrc": "345678/12/1", "tpin": "1001234569",
            "napsa_number": "9001234569", "nhima_number": "8001234569",
            "basic_salary": 8000.00, "position": "Junior Developer"
        },
        {
            "first_name": "Grace", "last_name": "Zulu",
            "email": "grace.zulu@demo.zm", "phone": "+260977444555",
            "nrc": "456789/13/1", "tpin": "1001234570",
            "napsa_number": "9001234570", "nhima_number": "8001234570",
            "basic_salary": 18000.00, "position": "Project Manager"
        },
        {
            "first_name": "David", "last_name": "Tembo",
            "email": "david.tembo@demo.zm", "phone": "+260966555666",
            "nrc": "567890/14/1", "tpin": "1001234571",
            "napsa_number": "9001234571", "nhima_number": "8001234571",
            "basic_salary": 6000.00, "position": "Intern"
        }
    ]
    
    employees = []
    
    for i, emp_data in enumerate(employees_data, 1):
        existing = db.query(models.Employee).filter(
            models.Employee.company_id == company_id,
            models.Employee.email == emp_data["email"]
        ).first()
        
        if existing:
            employees.append(existing)
            continue
        
        employee = models.Employee(
            company_id=company_id,
            employee_number=f"EMP{i:04d}",
            first_name=emp_data["first_name"],
            last_name=emp_data["last_name"],
            email=emp_data["email"],
            phone=emp_data["phone"],
            nrc_number=emp_data["nrc"],
            tpin=emp_data["tpin"],
            napsa_number=emp_data["napsa_number"],
            nhima_number=emp_data["nhima_number"],
            basic_salary=emp_data["basic_salary"],
            position=emp_data["position"],
            hire_date=date.today() - timedelta(days=random.randint(30, 730)),
            employment_status="active",
            employment_type="permanent"
        )
        
        db.add(employee)
        employees.append(employee)
    
    db.commit()
    
    return employees


def create_chart_of_accounts(db, company_id):
    """Create sample chart of accounts"""
    
    accounts_data = [
        {"code": "1000", "name": "Assets", "account_type": "asset"},
        {"code": "1100", "name": "Current Assets", "account_type": "asset", "parent": "1000"},
        {"code": "1110", "name": "Cash", "account_type": "asset", "parent": "1100"},
        {"code": "1120", "name": "Bank", "account_type": "asset", "parent": "1100"},
        {"code": "1130", "name": "Accounts Receivable", "account_type": "asset", "parent": "1100"},
        
        {"code": "2000", "name": "Liabilities", "account_type": "liability"},
        {"code": "2100", "name": "Current Liabilities", "account_type": "liability", "parent": "2000"},
        {"code": "2110", "name": "Accounts Payable", "account_type": "liability", "parent": "2100"},
        {"code": "2120", "name": "PAYE Payable", "account_type": "liability", "parent": "2100"},
        {"code": "2130", "name": "NAPSA Payable", "account_type": "liability", "parent": "2100"},
        {"code": "2140", "name": "NHIMA Payable", "account_type": "liability", "parent": "2100"},
        
        {"code": "3000", "name": "Equity", "account_type": "equity"},
        {"code": "3100", "name": "Share Capital", "account_type": "equity", "parent": "3000"},
        
        {"code": "4000", "name": "Revenue", "account_type": "revenue"},
        {"code": "4100", "name": "Sales Revenue", "account_type": "revenue", "parent": "4000"},
        
        {"code": "5000", "name": "Expenses", "account_type": "expense"},
        {"code": "5100", "name": "Salaries Expense", "account_type": "expense", "parent": "5000"},
        {"code": "5200", "name": "Rent Expense", "account_type": "expense", "parent": "5000"},
        {"code": "5300", "name": "Utilities Expense", "account_type": "expense", "parent": "5000"},
    ]
    
    accounts = []
    account_map = {}
    
    for acc_data in accounts_data:
        existing = db.query(models.Account).filter(
            models.Account.company_id == company_id,
            models.Account.code == acc_data["code"]
        ).first()
        
        if existing:
            accounts.append(existing)
            account_map[acc_data["code"]] = existing
            continue
        
        parent_id = None
        if "parent" in acc_data:
            parent = account_map.get(acc_data["parent"])
            if parent:
                parent_id = parent.id
        
        account = models.Account(
            company_id=company_id,
            code=acc_data["code"],
            name=acc_data["name"],
            account_type=acc_data["account_type"],
            parent_id=parent_id,
            is_active=True
        )
        
        db.add(account)
        db.flush()
        accounts.append(account)
        account_map[acc_data["code"]] = account
    
    db.commit()
    
    return accounts


def generate_obligations(db, company_id):
    """Generate statutory obligations for past 3 months"""
    
    compliance_service = StatutoryComplianceService(db, company_id)
    
    obligations = []
    today = date.today()
    
    for months_ago in range(3):
        target_date = today - timedelta(days=30 * months_ago)
        year = target_date.year
        month = target_date.month
        
        month_obligations = compliance_service.generate_monthly_obligations(year, month)
        obligations.extend(month_obligations)
    
    return obligations


def create_payrun(db, company_id, employees, user_id):
    """Create sample payrun"""
    
    today = date.today()
    year = today.year
    month = today.month
    
    existing = db.query(models.Payrun).filter(
        models.Payrun.company_id == company_id,
        models.Payrun.year == year,
        models.Payrun.month == month
    ).first()
    
    if existing:
        payslips = db.query(models.Payslip).filter(
            models.Payslip.payrun_id == existing.id
        ).all()
        return existing, payslips
    
    payrun = models.Payrun(
        company_id=company_id,
        year=year,
        month=month,
        pay_date=date(year, month, 25),
        status="draft",
        created_by=user_id
    )
    
    db.add(payrun)
    db.flush()
    
    payroll_service = PayrollService(db, company_id)
    payslips = payroll_service.calculate_payrun(payrun.id)
    
    db.commit()
    db.refresh(payrun)
    
    return payrun, payslips


def create_journal_entries(db, company_id, accounts, user_id):
    """Create sample journal entries"""
    
    account_map = {acc.code: acc for acc in accounts}
    
    entries_data = [
        {
            "description": "Initial capital investment",
            "lines": [
                {"code": "1120", "debit": 100000, "credit": 0},
                {"code": "3100", "debit": 0, "credit": 100000}
            ]
        },
        {
            "description": "Sales revenue for the month",
            "lines": [
                {"code": "1120", "debit": 50000, "credit": 0},
                {"code": "4100", "debit": 0, "credit": 50000}
            ]
        },
        {
            "description": "Rent payment",
            "lines": [
                {"code": "5200", "debit": 5000, "credit": 0},
                {"code": "1120", "debit": 0, "credit": 5000}
            ]
        }
    ]
    
    entries = []
    
    for i, entry_data in enumerate(entries_data, 1):
        entry = models.JournalEntry(
            company_id=company_id,
            entry_number=f"JE-{i:06d}",
            entry_date=date.today() - timedelta(days=random.randint(1, 30)),
            reference=f"REF-{i:04d}",
            description=entry_data["description"],
            status="posted",
            created_by=user_id,
            posted_by=user_id,
            posted_at=datetime.now()
        )
        
        db.add(entry)
        db.flush()
        
        for line_data in entry_data["lines"]:
            account = account_map.get(line_data["code"])
            if account:
                line = models.JournalEntryLine(
                    company_id=company_id,
                    entry_id=entry.id,
                    account_id=account.id,
                    debit=line_data["debit"],
                    credit=line_data["credit"],
                    description=entry_data["description"]
                )
                db.add(line)
        
        entries.append(entry)
    
    db.commit()
    
    return entries


if __name__ == "__main__":
    generate_sample_data()

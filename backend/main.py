from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
import models
import schemas
import auth
import utils
from database import engine, get_db
from ai_assistant import ai_assistant

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ERIK ERP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "ERIK ERP API is running", "version": "1.0.0"}

@app.post("/api/auth/register", response_model=schemas.Token)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    trial_end_date = datetime.utcnow() + timedelta(days=7)
    company = models.Company(
        name=user.company_name,
        currency="ZMW",
        subscription_plan="trial",
        subscription_status="active",
        trial_ends_at=trial_end_date
    )
    db.add(company)
    db.flush()
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role="admin",
        company_id=company.id
    )
    db.add(new_user)
    
    default_accounts = [
        {"code": "1000", "name": "Assets", "type": "asset"},
        {"code": "1100", "name": "Current Assets", "type": "asset", "parent": "1000"},
        {"code": "1110", "name": "Cash and Bank", "type": "asset", "parent": "1100"},
        {"code": "1120", "name": "Accounts Receivable", "type": "asset", "parent": "1100"},
        {"code": "2000", "name": "Liabilities", "type": "liability"},
        {"code": "2100", "name": "Current Liabilities", "type": "liability", "parent": "2000"},
        {"code": "2110", "name": "Accounts Payable", "type": "liability", "parent": "2100"},
        {"code": "3000", "name": "Equity", "type": "equity"},
        {"code": "4000", "name": "Revenue", "type": "revenue"},
        {"code": "5000", "name": "Expenses", "type": "expense"},
        {"code": "5100", "name": "Operating Expenses", "type": "expense", "parent": "5000"},
        {"code": "5200", "name": "Payroll Expenses", "type": "expense", "parent": "5000"},
    ]
    
    accounts_map = {}
    for acc_data in default_accounts:
        parent_code = acc_data.get("parent")
        parent_id = None
        if parent_code and parent_code in accounts_map:
            parent_id = accounts_map[parent_code]
        
        account = models.Account(
            company_id=company.id,
            code=acc_data["code"],
            name=acc_data["name"],
            account_type=acc_data["type"],
            parent_id=parent_id
        )
        db.add(account)
        db.flush()
        accounts_map[acc_data["code"]] = account.id
    
    db.commit()
    
    access_token = auth.create_access_token(data={"sub": new_user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    db_user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = auth.create_access_token(data={"sub": db_user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.get("/api/dashboard/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    
    total_employees = db.query(models.Employee).filter(
        models.Employee.company_id == current_user.company_id
    ).count()
    
    total_accounts = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id
    ).count()
    
    total_journals = db.query(models.JournalEntry).filter(
        models.JournalEntry.company_id == current_user.company_id
    ).count()
    
    return {
        "total_employees": total_employees,
        "total_accounts": total_accounts,
        "total_journals": total_journals,
        "company_name": company.name if company else "Unknown"
    }

@app.get("/api/employees", response_model=list[schemas.EmployeeResponse])
def get_employees(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    employees = db.query(models.Employee).filter(
        models.Employee.company_id == current_user.company_id
    ).all()
    return employees

@app.post("/api/employees", response_model=schemas.EmployeeResponse)
def create_employee(
    employee: schemas.EmployeeCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Validate department_id belongs to same company
    if employee.department_id:
        dept = db.query(models.Department).filter(
            models.Department.id == employee.department_id,
            models.Department.company_id == current_user.company_id
        ).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid department")
    
    new_employee = models.Employee(
        company_id=current_user.company_id,
        **employee.dict()
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee

@app.get("/api/accounts", response_model=list[schemas.AccountResponse])
def get_accounts(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    accounts = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id
    ).all()
    return accounts

@app.post("/api/accounts", response_model=schemas.AccountResponse)
def create_account(
    account: schemas.AccountCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if account.parent_id:
        parent = db.query(models.Account).filter(
            models.Account.id == account.parent_id,
            models.Account.company_id == current_user.company_id
        ).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent account not found or not accessible")
    
    new_account = models.Account(
        company_id=current_user.company_id,
        **account.dict()
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account

@app.get("/api/journals", response_model=list[schemas.JournalEntryResponse])
def get_journals(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    journals = db.query(models.JournalEntry).filter(
        models.JournalEntry.company_id == current_user.company_id
    ).order_by(models.JournalEntry.date.desc()).all()
    return journals

@app.post("/api/journals", response_model=schemas.JournalEntryResponse)
def create_journal(
    journal: schemas.JournalEntryCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if len(journal.lines) < 2:
        raise HTTPException(status_code=400, detail="Journal must have at least 2 lines (debit and credit)")
    
    # Validate department_id belongs to same company
    if journal.department_id:
        dept = db.query(models.Department).filter(
            models.Department.id == journal.department_id,
            models.Department.company_id == current_user.company_id
        ).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid department")
    
    # Validate branch_id belongs to same company
    if journal.branch_id:
        branch = db.query(models.Branch).filter(
            models.Branch.id == journal.branch_id,
            models.Branch.company_id == current_user.company_id
        ).first()
        if not branch:
            raise HTTPException(status_code=400, detail="Invalid branch")
    
    total_debits = sum(line.amount for line in journal.lines if line.side == "debit")
    total_credits = sum(line.amount for line in journal.lines if line.side == "credit")
    
    if abs(total_debits - total_credits) > 0.01:
        raise HTTPException(
            status_code=400, 
            detail=f"Debits ({total_debits}) must equal credits ({total_credits})"
        )
    
    for line in journal.lines:
        account = db.query(models.Account).filter(
            models.Account.id == line.account_id,
            models.Account.company_id == current_user.company_id
        ).first()
        if not account:
            raise HTTPException(
                status_code=400, 
                detail=f"Account {line.account_id} not found or not accessible"
            )
    
    journal_count = db.query(models.JournalEntry).filter(
        models.JournalEntry.company_id == current_user.company_id
    ).count()
    
    journal_number = f"JE-{journal_count + 1:05d}"
    
    new_journal = models.JournalEntry(
        company_id=current_user.company_id,
        journal_number=journal_number,
        date=journal.date,
        description=journal.description,
        currency=journal.currency,
        total_amount=total_debits,
        department_id=journal.department_id,
        branch_id=journal.branch_id,
        created_by=current_user.id,
        status="posted"
    )
    db.add(new_journal)
    db.flush()
    
    for line in journal.lines:
        journal_line = models.JournalLine(
            journal_id=new_journal.id,
            **line.dict()
        )
        db.add(journal_line)
    
    db.commit()
    db.refresh(new_journal)
    return new_journal

@app.get("/api/products", response_model=list[schemas.ProductResponse])
def get_products(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    products = db.query(models.Product).filter(
        models.Product.company_id == current_user.company_id
    ).all()
    return products

@app.post("/api/products", response_model=schemas.ProductResponse)
def create_product(
    product: schemas.ProductCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    new_product = models.Product(
        company_id=current_user.company_id,
        **product.dict()
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@app.get("/api/warehouses", response_model=list[schemas.WarehouseResponse])
def get_warehouses(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    warehouses = db.query(models.Warehouse).filter(
        models.Warehouse.company_id == current_user.company_id
    ).all()
    return warehouses

@app.post("/api/warehouses", response_model=schemas.WarehouseResponse)
def create_warehouse(
    warehouse: schemas.WarehouseCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    new_warehouse = models.Warehouse(
        company_id=current_user.company_id,
        **warehouse.dict()
    )
    db.add(new_warehouse)
    db.commit()
    db.refresh(new_warehouse)
    return new_warehouse

@app.get("/api/customers", response_model=list[schemas.CustomerResponse])
def get_customers(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    customers = db.query(models.Customer).filter(
        models.Customer.company_id == current_user.company_id
    ).all()
    return customers

@app.post("/api/customers", response_model=schemas.CustomerResponse)
def create_customer(
    customer: schemas.CustomerCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    new_customer = models.Customer(
        company_id=current_user.company_id,
        **customer.dict()
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

@app.get("/api/suppliers", response_model=list[schemas.SupplierResponse])
def get_suppliers(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    suppliers = db.query(models.Supplier).filter(
        models.Supplier.company_id == current_user.company_id
    ).all()
    return suppliers

@app.post("/api/suppliers", response_model=schemas.SupplierResponse)
def create_supplier(
    supplier: schemas.SupplierCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    new_supplier = models.Supplier(
        company_id=current_user.company_id,
        **supplier.dict()
    )
    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)
    return new_supplier

@app.get("/api/purchase-orders", response_model=list[schemas.PurchaseOrderResponse])
def get_purchase_orders(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    orders = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.company_id == current_user.company_id
    ).order_by(models.PurchaseOrder.order_date.desc()).all()
    return orders

@app.post("/api/purchase-orders", response_model=schemas.PurchaseOrderResponse)
def create_purchase_order(
    po: schemas.PurchaseOrderCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    supplier = db.query(models.Supplier).filter(
        models.Supplier.id == po.supplier_id,
        models.Supplier.company_id == current_user.company_id
    ).first()
    if not supplier:
        raise HTTPException(status_code=400, detail="Supplier not found")
    
    # Validate department_id belongs to same company
    if po.department_id:
        dept = db.query(models.Department).filter(
            models.Department.id == po.department_id,
            models.Department.company_id == current_user.company_id
        ).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid department")
    
    # Validate branch_id belongs to same company
    if po.branch_id:
        branch = db.query(models.Branch).filter(
            models.Branch.id == po.branch_id,
            models.Branch.company_id == current_user.company_id
        ).first()
        if not branch:
            raise HTTPException(status_code=400, detail="Invalid branch")
    
    for line in po.lines:
        product = db.query(models.Product).filter(
            models.Product.id == line.product_id,
            models.Product.company_id == current_user.company_id
        ).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {line.product_id} not found")
    
    po_count = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.company_id == current_user.company_id
    ).count()
    po_number = f"PO-{po_count + 1:05d}"
    
    total = sum(line.quantity * line.unit_price for line in po.lines)
    
    new_po = models.PurchaseOrder(
        company_id=current_user.company_id,
        supplier_id=po.supplier_id,
        po_number=po_number,
        order_date=po.order_date,
        expected_delivery=po.expected_delivery,
        department_id=po.department_id,
        branch_id=po.branch_id,
        total_amount=total,
        notes=po.notes,
        created_by=current_user.id,
        status="draft"
    )
    db.add(new_po)
    db.flush()
    
    for line in po.lines:
        po_line = models.PurchaseOrderLine(
            purchase_order_id=new_po.id,
            product_id=line.product_id,
            quantity=line.quantity,
            unit_price=line.unit_price,
            subtotal=line.quantity * line.unit_price
        )
        db.add(po_line)
    
    db.commit()
    db.refresh(new_po)
    return new_po

@app.get("/api/sales-orders", response_model=list[schemas.SalesOrderResponse])
def get_sales_orders(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    orders = db.query(models.SalesOrder).filter(
        models.SalesOrder.company_id == current_user.company_id
    ).order_by(models.SalesOrder.order_date.desc()).all()
    return orders

@app.post("/api/sales-orders", response_model=schemas.SalesOrderResponse)
def create_sales_order(
    so: schemas.SalesOrderCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    customer = db.query(models.Customer).filter(
        models.Customer.id == so.customer_id,
        models.Customer.company_id == current_user.company_id
    ).first()
    if not customer:
        raise HTTPException(status_code=400, detail="Customer not found")
    
    # Validate department_id belongs to same company
    if so.department_id:
        dept = db.query(models.Department).filter(
            models.Department.id == so.department_id,
            models.Department.company_id == current_user.company_id
        ).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid department")
    
    # Validate branch_id belongs to same company
    if so.branch_id:
        branch = db.query(models.Branch).filter(
            models.Branch.id == so.branch_id,
            models.Branch.company_id == current_user.company_id
        ).first()
        if not branch:
            raise HTTPException(status_code=400, detail="Invalid branch")
    
    for line in so.lines:
        product = db.query(models.Product).filter(
            models.Product.id == line.product_id,
            models.Product.company_id == current_user.company_id
        ).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {line.product_id} not found")
    
    so_count = db.query(models.SalesOrder).filter(
        models.SalesOrder.company_id == current_user.company_id
    ).count()
    so_number = f"SO-{so_count + 1:05d}"
    
    total = sum(line.quantity * line.unit_price for line in so.lines)
    
    new_so = models.SalesOrder(
        company_id=current_user.company_id,
        customer_id=so.customer_id,
        so_number=so_number,
        order_date=so.order_date,
        delivery_date=so.delivery_date,
        department_id=so.department_id,
        branch_id=so.branch_id,
        total_amount=total,
        notes=so.notes,
        created_by=current_user.id,
        status="draft"
    )
    db.add(new_so)
    db.flush()
    
    for line in so.lines:
        so_line = models.SalesOrderLine(
            sales_order_id=new_so.id,
            product_id=line.product_id,
            quantity=line.quantity,
            unit_price=line.unit_price,
            subtotal=line.quantity * line.unit_price
        )
        db.add(so_line)
    
    db.commit()
    db.refresh(new_so)
    return new_so

@app.get("/api/leave-types", response_model=list[schemas.LeaveTypeResponse])
def get_leave_types(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    leave_types = db.query(models.LeaveType).filter(
        models.LeaveType.company_id == current_user.company_id
    ).all()
    return leave_types

@app.post("/api/leave-types", response_model=schemas.LeaveTypeResponse)
def create_leave_type(
    leave_type: schemas.LeaveTypeCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    new_leave_type = models.LeaveType(
        company_id=current_user.company_id,
        **leave_type.dict()
    )
    db.add(new_leave_type)
    db.commit()
    db.refresh(new_leave_type)
    return new_leave_type

@app.get("/api/leave-applications", response_model=list[schemas.LeaveApplicationResponse])
def get_leave_applications(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    applications = db.query(models.LeaveApplication).filter(
        models.LeaveApplication.company_id == current_user.company_id
    ).order_by(models.LeaveApplication.created_at.desc()).all()
    return applications

@app.post("/api/leave-applications", response_model=schemas.LeaveApplicationResponse)
def create_leave_application(
    application: schemas.LeaveApplicationCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    employee = db.query(models.Employee).filter(
        models.Employee.id == application.employee_id,
        models.Employee.company_id == current_user.company_id
    ).first()
    if not employee:
        raise HTTPException(status_code=400, detail="Employee not found")
    
    leave_type = db.query(models.LeaveType).filter(
        models.LeaveType.id == application.leave_type_id,
        models.LeaveType.company_id == current_user.company_id
    ).first()
    if not leave_type:
        raise HTTPException(status_code=400, detail="Leave type not found")
    
    app_count = db.query(models.LeaveApplication).filter(
        models.LeaveApplication.company_id == current_user.company_id
    ).count()
    app_number = f"LA-{app_count + 1:05d}"
    
    new_application = models.LeaveApplication(
        company_id=current_user.company_id,
        application_number=app_number,
        **application.dict()
    )
    db.add(new_application)
    db.commit()
    db.refresh(new_application)
    return new_application

@app.get("/api/payslips", response_model=list[schemas.PayslipResponse])
def get_payslips(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    payslips = db.query(models.Payslip).filter(
        models.Payslip.company_id == current_user.company_id
    ).order_by(models.Payslip.period_year.desc(), models.Payslip.period_month.desc()).all()
    return payslips

@app.post("/api/payslips", response_model=schemas.PayslipResponse)
def create_payslip(
    payslip: schemas.PayslipCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    employee = db.query(models.Employee).filter(
        models.Employee.id == payslip.employee_id,
        models.Employee.company_id == current_user.company_id
    ).first()
    if not employee:
        raise HTTPException(status_code=400, detail="Employee not found")
    
    payslip_count = db.query(models.Payslip).filter(
        models.Payslip.company_id == current_user.company_id
    ).count()
    payslip_number = f"PAY-{payslip_count + 1:05d}"
    
    payslip_data = utils.generate_payslip_data(employee, payslip.period_month, payslip.period_year)
    
    new_payslip = models.Payslip(
        company_id=current_user.company_id,
        employee_id=payslip.employee_id,
        payslip_number=payslip_number,
        **payslip_data,
        status="draft"
    )
    db.add(new_payslip)
    db.commit()
    db.refresh(new_payslip)
    return new_payslip

@app.post("/api/reports/financial", response_model=schemas.FinancialReport)
def generate_financial_report(
    report_request: schemas.FinancialReportRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if report_request.report_type == "income_statement":
        return utils.generate_income_statement(
            db, 
            current_user.company_id, 
            report_request.start_date, 
            report_request.end_date
        )
    elif report_request.report_type == "balance_sheet":
        return utils.generate_balance_sheet(
            db, 
            current_user.company_id, 
            report_request.end_date
        )
    elif report_request.report_type == "cash_flow":
        return utils.generate_cash_flow(
            db, 
            current_user.company_id, 
            report_request.start_date, 
            report_request.end_date
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid report type")

@app.get("/api/admin/companies", response_model=list[schemas.CompanyAdminResponse])
def admin_get_all_companies(
    admin: models.User = Depends(auth.get_super_admin),
    db: Session = Depends(get_db)
):
    companies = db.query(models.Company).order_by(models.Company.created_at.desc()).all()
    return companies

@app.put("/api/admin/companies/{company_id}/toggle-status")
def admin_toggle_company_status(
    company_id: str,
    admin: models.User = Depends(auth.get_super_admin),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.is_active = not company.is_active
    db.commit()
    return {"message": f"Company {'activated' if company.is_active else 'deactivated'} successfully"}

@app.put("/api/admin/companies/{company_id}/subscription")
def admin_update_subscription(
    company_id: str,
    plan: str,
    status: str,
    admin: models.User = Depends(auth.get_super_admin),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.subscription_plan = plan
    company.subscription_status = status
    if plan != "trial":
        company.subscription_ends_at = datetime.utcnow() + timedelta(days=30)
    db.commit()
    return {"message": "Subscription updated successfully"}

@app.get("/api/admin/stats", response_model=schemas.SystemStatsResponse)
def admin_get_system_stats(
    admin: models.User = Depends(auth.get_super_admin),
    db: Session = Depends(get_db)
):
    total_companies = db.query(models.Company).count()
    active_companies = db.query(models.Company).filter(models.Company.is_active == True).count()
    trial_companies = db.query(models.Company).filter(models.Company.subscription_plan == "trial").count()
    paid_companies = db.query(models.Company).filter(models.Company.subscription_plan != "trial").count()
    total_users = db.query(models.User).filter(models.User.role != "super_admin").count()
    total_employees = db.query(models.Employee).count()
    total_transactions = db.query(models.JournalEntry).count()
    
    return {
        "total_companies": total_companies,
        "active_companies": active_companies,
        "trial_companies": trial_companies,
        "paid_companies": paid_companies,
        "total_users": total_users,
        "total_employees": total_employees,
        "total_transactions": total_transactions,
        "total_revenue": 0.0
    }

@app.get("/api/admin/analytics")
def admin_get_analytics(
    admin: models.User = Depends(auth.get_super_admin),
    db: Session = Depends(get_db)
):
    companies = db.query(models.Company).all()
    analytics = []
    
    for company in companies:
        user_count = db.query(models.User).filter(models.User.company_id == company.id).count()
        employee_count = db.query(models.Employee).filter(models.Employee.company_id == company.id).count()
        transaction_count = db.query(models.JournalEntry).filter(models.JournalEntry.company_id == company.id).count()
        
        analytics.append({
            "company_id": company.id,
            "company_name": company.name,
            "subscription_plan": company.subscription_plan,
            "subscription_status": company.subscription_status,
            "trial_ends_at": company.trial_ends_at,
            "is_active": company.is_active,
            "user_count": user_count,
            "employee_count": employee_count,
            "transaction_count": transaction_count,
            "created_at": company.created_at
        })
    
    return {"analytics": analytics}

@app.get("/api/mobile-money/providers", response_model=list[schemas.MobileMoneyProviderResponse])
def get_mm_providers(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    providers = db.query(models.MobileMoneyProvider).filter(
        models.MobileMoneyProvider.company_id == current_user.company_id
    ).all()
    return providers

@app.post("/api/mobile-money/providers", response_model=schemas.MobileMoneyProviderResponse)
def create_mm_provider(
    provider: schemas.MobileMoneyProviderCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    new_provider = models.MobileMoneyProvider(
        company_id=current_user.company_id,
        **provider.dict()
    )
    db.add(new_provider)
    db.commit()
    db.refresh(new_provider)
    return new_provider

@app.get("/api/mobile-money/transactions", response_model=list[schemas.MobileMoneyTransactionResponse])
def get_mm_transactions(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    transactions = db.query(models.MobileMoneyTransaction).filter(
        models.MobileMoneyTransaction.company_id == current_user.company_id
    ).order_by(models.MobileMoneyTransaction.created_at.desc()).all()
    return transactions

@app.post("/api/mobile-money/transactions", response_model=schemas.MobileMoneyTransactionResponse)
def create_mm_transaction(
    transaction: schemas.MobileMoneyTransactionCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    provider = db.query(models.MobileMoneyProvider).filter(
        models.MobileMoneyProvider.id == transaction.provider_id,
        models.MobileMoneyProvider.company_id == current_user.company_id
    ).first()
    if not provider:
        raise HTTPException(status_code=400, detail="Provider not found")
    
    tx_count = db.query(models.MobileMoneyTransaction).filter(
        models.MobileMoneyTransaction.company_id == current_user.company_id
    ).count()
    tx_ref = f"MM-{tx_count + 1:06d}"
    
    new_transaction = models.MobileMoneyTransaction(
        company_id=current_user.company_id,
        transaction_ref=tx_ref,
        initiated_by=current_user.id,
        **transaction.dict()
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)
    return new_transaction

@app.put("/api/mobile-money/providers/{provider_id}")
def update_mm_provider(
    provider_id: str,
    is_active: bool,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    provider = db.query(models.MobileMoneyProvider).filter(
        models.MobileMoneyProvider.id == provider_id,
        models.MobileMoneyProvider.company_id == current_user.company_id
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    provider.is_active = is_active
    db.commit()
    return {"message": "Provider updated"}

@app.delete("/api/mobile-money/providers/{provider_id}")
def delete_mm_provider(
    provider_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    provider = db.query(models.MobileMoneyProvider).filter(
        models.MobileMoneyProvider.id == provider_id,
        models.MobileMoneyProvider.company_id == current_user.company_id
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    db.delete(provider)
    db.commit()
    return {"message": "Provider deleted"}

@app.get("/api/branches", response_model=list[schemas.BranchResponse])
def get_branches(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    branches = db.query(models.Branch).filter(
        models.Branch.company_id == current_user.company_id
    ).all()
    return branches

@app.post("/api/branches", response_model=schemas.BranchResponse)
def create_branch(
    branch: schemas.BranchCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if branch.manager_id:
        manager = db.query(models.Employee).filter(
            models.Employee.id == branch.manager_id,
            models.Employee.company_id == current_user.company_id
        ).first()
        if not manager:
            raise HTTPException(status_code=400, detail="Manager not found")
    
    new_branch = models.Branch(
        company_id=current_user.company_id,
        **branch.dict()
    )
    db.add(new_branch)
    db.commit()
    db.refresh(new_branch)
    return new_branch

@app.put("/api/branches/{branch_id}")
def update_branch(
    branch_id: str,
    is_active: bool,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    branch = db.query(models.Branch).filter(
        models.Branch.id == branch_id,
        models.Branch.company_id == current_user.company_id
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    branch.is_active = is_active
    db.commit()
    return {"message": "Branch updated"}

@app.delete("/api/branches/{branch_id}")
def delete_branch(
    branch_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    branch = db.query(models.Branch).filter(
        models.Branch.id == branch_id,
        models.Branch.company_id == current_user.company_id
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    db.delete(branch)
    db.commit()
    return {"message": "Branch deleted"}

@app.get("/api/branch-transfers", response_model=list[schemas.BranchTransferResponse])
def get_branch_transfers(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    transfers = db.query(models.BranchTransfer).filter(
        models.BranchTransfer.company_id == current_user.company_id
    ).order_by(models.BranchTransfer.created_at.desc()).all()
    return transfers

@app.post("/api/branch-transfers", response_model=schemas.BranchTransferResponse)
def create_branch_transfer(
    transfer: schemas.BranchTransferCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    from_branch = db.query(models.Branch).filter(
        models.Branch.id == transfer.from_branch_id,
        models.Branch.company_id == current_user.company_id
    ).first()
    if not from_branch:
        raise HTTPException(status_code=400, detail="From branch not found")
    
    to_branch = db.query(models.Branch).filter(
        models.Branch.id == transfer.to_branch_id,
        models.Branch.company_id == current_user.company_id
    ).first()
    if not to_branch:
        raise HTTPException(status_code=400, detail="To branch not found")
    
    for line in transfer.lines:
        product = db.query(models.Product).filter(
            models.Product.id == line['product_id'],
            models.Product.company_id == current_user.company_id
        ).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {line['product_id']} not found")
    
    transfer_count = db.query(models.BranchTransfer).filter(
        models.BranchTransfer.company_id == current_user.company_id
    ).count()
    transfer_number = f"BT-{transfer_count + 1:05d}"
    
    new_transfer = models.BranchTransfer(
        company_id=current_user.company_id,
        transfer_number=transfer_number,
        from_branch_id=transfer.from_branch_id,
        to_branch_id=transfer.to_branch_id,
        transfer_date=transfer.transfer_date,
        notes=transfer.notes,
        initiated_by=current_user.id
    )
    db.add(new_transfer)
    db.flush()
    
    for line in transfer.lines:
        transfer_line = models.BranchTransferLine(
            transfer_id=new_transfer.id,
            product_id=line['product_id'],
            quantity=line['quantity']
        )
        db.add(transfer_line)
    
    db.commit()
    db.refresh(new_transfer)
    return new_transfer

@app.get("/api/pos/terminals", response_model=list[schemas.POSTerminalResponse])
def get_pos_terminals(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    terminals = db.query(models.POSTerminal).filter(
        models.POSTerminal.company_id == current_user.company_id
    ).all()
    return terminals

@app.post("/api/pos/terminals", response_model=schemas.POSTerminalResponse)
def create_pos_terminal(
    terminal: schemas.POSTerminalCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if terminal.branch_id:
        branch = db.query(models.Branch).filter(
            models.Branch.id == terminal.branch_id,
            models.Branch.company_id == current_user.company_id
        ).first()
        if not branch:
            raise HTTPException(status_code=400, detail="Branch not found")
    
    new_terminal = models.POSTerminal(
        company_id=current_user.company_id,
        **terminal.dict()
    )
    db.add(new_terminal)
    db.commit()
    db.refresh(new_terminal)
    return new_terminal

@app.put("/api/pos/terminals/{terminal_id}")
def update_pos_terminal(
    terminal_id: str,
    is_active: bool,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    terminal = db.query(models.POSTerminal).filter(
        models.POSTerminal.id == terminal_id,
        models.POSTerminal.company_id == current_user.company_id
    ).first()
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    
    terminal.is_active = is_active
    db.commit()
    return {"message": "Terminal updated"}

@app.delete("/api/pos/terminals/{terminal_id}")
def delete_pos_terminal(
    terminal_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    terminal = db.query(models.POSTerminal).filter(
        models.POSTerminal.id == terminal_id,
        models.POSTerminal.company_id == current_user.company_id
    ).first()
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    
    db.delete(terminal)
    db.commit()
    return {"message": "Terminal deleted"}

@app.get("/api/pos/sales", response_model=list[schemas.POSSaleResponse])
def get_pos_sales(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    sales = db.query(models.POSSale).filter(
        models.POSSale.company_id == current_user.company_id
    ).order_by(models.POSSale.sale_date.desc()).all()
    return sales

@app.post("/api/pos/sales", response_model=schemas.POSSaleResponse)
def create_pos_sale(
    sale: schemas.POSSaleCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    for line in sale.lines:
        product = db.query(models.Product).filter(
            models.Product.id == line['product_id'],
            models.Product.company_id == current_user.company_id
        ).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {line['product_id']} not found")
    
    sale_count = db.query(models.POSSale).filter(
        models.POSSale.company_id == current_user.company_id
    ).count()
    receipt_number = f"RCT-{sale_count + 1:06d}"
    
    total = sum(line['quantity'] * line['unit_price'] for line in sale.lines)
    
    new_sale = models.POSSale(
        company_id=current_user.company_id,
        receipt_number=receipt_number,
        branch_id=sale.branch_id,
        terminal_id=sale.terminal_id,
        customer_id=sale.customer_id,
        total_amount=total,
        payment_method=sale.payment_method,
        payment_ref=sale.payment_ref,
        cashier_id=current_user.id
    )
    db.add(new_sale)
    db.flush()
    
    for line in sale.lines:
        sale_line = models.POSSaleLine(
            sale_id=new_sale.id,
            product_id=line['product_id'],
            quantity=line['quantity'],
            unit_price=line['unit_price'],
            subtotal=line['quantity'] * line['unit_price']
        )
        db.add(sale_line)
    
    db.commit()
    db.refresh(new_sale)
    return new_sale

@app.get("/api/pos/sessions", response_model=list[schemas.CashierSessionResponse])
def get_cashier_sessions(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(models.CashierSession).filter(
        models.CashierSession.company_id == current_user.company_id
    ).order_by(models.CashierSession.session_start.desc()).all()
    return sessions

@app.post("/api/pos/sessions", response_model=schemas.CashierSessionResponse)
def create_cashier_session(
    session: schemas.CashierSessionCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    terminal = db.query(models.POSTerminal).filter(
        models.POSTerminal.id == session.terminal_id,
        models.POSTerminal.company_id == current_user.company_id
    ).first()
    if not terminal:
        raise HTTPException(status_code=400, detail="Terminal not found")
    
    new_session = models.CashierSession(
        company_id=current_user.company_id,
        cashier_id=current_user.id,
        **session.dict()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

# Statutory Obligations Endpoints
@app.get("/api/statutory-obligations")
def get_statutory_obligations(
    status: Optional[str] = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all statutory obligations for the company"""
    query = db.query(models.StatutoryObligation).filter(
        models.StatutoryObligation.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.StatutoryObligation.status == status)
    
    obligations = query.order_by(models.StatutoryObligation.due_date).all()
    return obligations

@app.post("/api/statutory-obligations", response_model=schemas.StatutoryObligationResponse)
def create_statutory_obligation(
    obligation: schemas.StatutoryObligationCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new statutory obligation"""
    # Validate and create with only whitelisted fields
    new_obligation = models.StatutoryObligation(
        company_id=current_user.company_id,
        **obligation.dict()
    )
    db.add(new_obligation)
    db.commit()
    db.refresh(new_obligation)
    return new_obligation

@app.put("/api/statutory-obligations/{obligation_id}", response_model=schemas.StatutoryObligationResponse)
def update_statutory_obligation(
    obligation_id: str,
    obligation: schemas.StatutoryObligationUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update statutory obligation with validated fields only"""
    # Enforce multi-tenant security: verify company ownership
    db_obligation = db.query(models.StatutoryObligation).filter(
        models.StatutoryObligation.id == obligation_id,
        models.StatutoryObligation.company_id == current_user.company_id
    ).first()
    
    if not db_obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")
    
    # Only update fields that are present in the request (exclude None values)
    update_data = obligation.dict(exclude_unset=True, exclude_none=True)
    
    # Apply validated fields only - Pydantic schema ensures no protected fields
    for key, value in update_data.items():
        setattr(db_obligation, key, value)
    
    db.commit()
    db.refresh(db_obligation)
    return db_obligation

@app.get("/api/statutory-obligations/dashboard")
def get_statutory_dashboard(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get statutory obligations dashboard data"""
    from datetime import date, timedelta
    
    today = date.today()
    next_30_days = today + timedelta(days=30)
    
    # Get all obligations
    all_obligations = db.query(models.StatutoryObligation).filter(
        models.StatutoryObligation.company_id == current_user.company_id
    ).all()
    
    # Get upcoming obligations (next 30 days)
    upcoming = db.query(models.StatutoryObligation).filter(
        models.StatutoryObligation.company_id == current_user.company_id,
        models.StatutoryObligation.due_date >= today,
        models.StatutoryObligation.due_date <= next_30_days,
        models.StatutoryObligation.status == "pending"
    ).order_by(models.StatutoryObligation.due_date).all()
    
    # Get overdue obligations
    overdue = db.query(models.StatutoryObligation).filter(
        models.StatutoryObligation.company_id == current_user.company_id,
        models.StatutoryObligation.due_date < today,
        models.StatutoryObligation.status == "pending"
    ).all()
    
    # Calculate total amounts
    total_due = sum(o.amount or 0 for o in upcoming)
    total_overdue = sum(o.amount or 0 for o in overdue)
    
    return {
        "total_obligations": len(all_obligations),
        "upcoming_count": len(upcoming),
        "overdue_count": len(overdue),
        "total_due_amount": total_due,
        "total_overdue_amount": total_overdue,
        "upcoming_obligations": upcoming,
        "overdue_obligations": overdue
    }

# AI Assistant Endpoints
@app.post("/api/ai/chat")
async def ai_chat(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to ERIK AI Assistant"""
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    
    user_context = {
        "company_name": company.name,
        "user_name": current_user.full_name,
        "role": current_user.role
    }
    
    result = await ai_assistant.chat(
        message=message,
        conversation_history=conversation_history,
        user_context=user_context
    )
    
    return result

@app.post("/api/ai/analyze-report")
async def ai_analyze_report(
    report_type: str,
    data: Dict[str, Any],
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze financial reports with AI"""
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    
    user_context = {
        "company_name": company.name,
        "user_name": current_user.full_name,
        "role": current_user.role
    }
    
    result = await ai_assistant.analyze_financial_report(
        report_type=report_type,
        data=data,
        user_context=user_context
    )
    
    return result

@app.post("/api/ai/explain-compliance")
async def ai_explain_compliance(
    compliance_type: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get explanation of Zambian statutory compliance requirements"""
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    
    user_context = {
        "company_name": company.name,
        "user_name": current_user.full_name,
        "role": current_user.role
    }
    
    result = await ai_assistant.explain_statutory_compliance(
        compliance_type=compliance_type,
        user_context=user_context
    )
    
    return result

@app.post("/api/ai/generate-summary")
async def ai_generate_summary(
    data_type: str,
    data: Dict[str, Any],
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Generate executive summary of business data"""
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    
    user_context = {
        "company_name": company.name,
        "user_name": current_user.full_name,
        "role": current_user.role
    }
    
    result = await ai_assistant.generate_summary(
        data_type=data_type,
        data=data,
        user_context=user_context
    )
    
    return result

# Department Management Endpoints
@app.get("/api/departments", response_model=List[schemas.DepartmentResponse])
def get_departments(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all departments for the company"""
    departments = db.query(models.Department).filter(
        models.Department.company_id == current_user.company_id
    ).order_by(models.Department.dept_code).all()
    return departments

@app.post("/api/departments", response_model=schemas.DepartmentResponse)
def create_department(
    department: schemas.DepartmentCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new department with multi-tenant security validation"""
    # Check for duplicate dept_code
    existing = db.query(models.Department).filter(
        models.Department.company_id == current_user.company_id,
        models.Department.dept_code == department.dept_code
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Department code already exists")
    
    # Validate parent_dept_id belongs to same company
    if department.parent_dept_id:
        parent = db.query(models.Department).filter(
            models.Department.id == department.parent_dept_id,
            models.Department.company_id == current_user.company_id
        ).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Invalid parent department")
    
    # Validate manager_id belongs to same company
    if department.manager_id:
        manager = db.query(models.User).filter(
            models.User.id == department.manager_id,
            models.User.company_id == current_user.company_id
        ).first()
        if not manager:
            raise HTTPException(status_code=400, detail="Invalid manager user")
    
    new_dept = models.Department(
        company_id=current_user.company_id,
        **department.dict()
    )
    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)
    return new_dept

@app.put("/api/departments/{dept_id}", response_model=schemas.DepartmentResponse)
def update_department(
    dept_id: str,
    department: schemas.DepartmentUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update a department with multi-tenant security validation"""
    db_dept = db.query(models.Department).filter(
        models.Department.id == dept_id,
        models.Department.company_id == current_user.company_id
    ).first()
    
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    update_data = department.dict(exclude_unset=True, exclude_none=True)
    
    # Validate parent_dept_id belongs to same company
    if 'parent_dept_id' in update_data and update_data['parent_dept_id']:
        parent = db.query(models.Department).filter(
            models.Department.id == update_data['parent_dept_id'],
            models.Department.company_id == current_user.company_id
        ).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Invalid parent department")
    
    # Validate manager_id belongs to same company
    if 'manager_id' in update_data and update_data['manager_id']:
        manager = db.query(models.User).filter(
            models.User.id == update_data['manager_id'],
            models.User.company_id == current_user.company_id
        ).first()
        if not manager:
            raise HTTPException(status_code=400, detail="Invalid manager user")
    
    for key, value in update_data.items():
        setattr(db_dept, key, value)
    
    db.commit()
    db.refresh(db_dept)
    return db_dept

# Consolidated Reporting Endpoints
@app.get("/api/reports/consolidated-pl")
def get_consolidated_pl_report(
    start_date: date,
    end_date: date,
    group_by: str = "department",
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get consolidated Profit & Loss report by department/branch/company"""
    from sqlalchemy import func
    
    query = db.query(
        models.JournalLine.account_id,
        models.Account.name.label("account_name"),
        models.Account.account_type,
        func.sum(models.JournalLine.amount).label("total_amount")
    ).join(
        models.JournalEntry, models.JournalLine.journal_id == models.JournalEntry.id
    ).join(
        models.Account, models.JournalLine.account_id == models.Account.id
    ).filter(
        models.JournalEntry.company_id == current_user.company_id,
        models.JournalEntry.date >= start_date,
        models.JournalEntry.date <= end_date,
        models.JournalEntry.status == "posted",
        models.Account.account_type.in_(["revenue", "expense"])
    )
    
    if group_by == "department":
        query = query.add_columns(
            models.JournalEntry.department_id,
            models.Department.dept_name
        ).outerjoin(
            models.Department, models.JournalEntry.department_id == models.Department.id
        ).group_by(
            models.JournalLine.account_id,
            models.Account.name,
            models.Account.account_type,
            models.JournalEntry.department_id,
            models.Department.dept_name
        )
    elif group_by == "branch":
        query = query.add_columns(
            models.JournalEntry.branch_id,
            models.Branch.branch_name
        ).outerjoin(
            models.Branch, models.JournalEntry.branch_id == models.Branch.id
        ).group_by(
            models.JournalLine.account_id,
            models.Account.name,
            models.Account.account_type,
            models.JournalEntry.branch_id,
            models.Branch.branch_name
        )
    else:
        query = query.group_by(
            models.JournalLine.account_id,
            models.Account.name,
            models.Account.account_type
        )
    
    results = query.all()
    
    report_data = {}
    for row in results:
        if group_by == "department":
            group_key = f"{row.dept_name or 'Unassigned'}"
        elif group_by == "branch":
            group_key = f"{row.branch_name or 'Unassigned'}"
        else:
            group_key = "Company Total"
        
        if group_key not in report_data:
            report_data[group_key] = {
                "income": {},
                "expenses": {},
                "total_income": 0.0,
                "total_expenses": 0.0,
                "net_profit": 0.0
            }
        
        if row.account_type == "revenue":
            report_data[group_key]["income"][row.account_name] = float(row.total_amount)
            report_data[group_key]["total_income"] += float(row.total_amount)
        elif row.account_type == "expense":
            report_data[group_key]["expenses"][row.account_name] = float(row.total_amount)
            report_data[group_key]["total_expenses"] += float(row.total_amount)
        
        report_data[group_key]["net_profit"] = (
            report_data[group_key]["total_income"] - report_data[group_key]["total_expenses"]
        )
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "group_by": group_by,
        "report_data": report_data
    }

@app.get("/api/reports/consolidated-balance-sheet")
def get_consolidated_balance_sheet(
    as_of_date: date,
    group_by: str = "department",
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get consolidated Balance Sheet by department/branch/company"""
    from sqlalchemy import func
    
    query = db.query(
        models.JournalLine.account_id,
        models.Account.name.label("account_name"),
        models.Account.account_type,
        func.sum(
            func.case(
                (models.JournalLine.side == "debit", models.JournalLine.amount),
                else_=-models.JournalLine.amount
            )
        ).label("balance")
    ).join(
        models.JournalEntry, models.JournalLine.journal_id == models.JournalEntry.id
    ).join(
        models.Account, models.JournalLine.account_id == models.Account.id
    ).filter(
        models.JournalEntry.company_id == current_user.company_id,
        models.JournalEntry.date <= as_of_date,
        models.JournalEntry.status == "posted",
        models.Account.account_type.in_(["asset", "liability", "equity"])
    )
    
    if group_by == "department":
        query = query.add_columns(
            models.JournalEntry.department_id,
            models.Department.dept_name
        ).outerjoin(
            models.Department, models.JournalEntry.department_id == models.Department.id
        ).group_by(
            models.JournalLine.account_id,
            models.Account.name,
            models.Account.account_type,
            models.JournalEntry.department_id,
            models.Department.dept_name
        )
    elif group_by == "branch":
        query = query.add_columns(
            models.JournalEntry.branch_id,
            models.Branch.branch_name
        ).outerjoin(
            models.Branch, models.JournalEntry.branch_id == models.Branch.id
        ).group_by(
            models.JournalLine.account_id,
            models.Account.name,
            models.Account.account_type,
            models.JournalEntry.branch_id,
            models.Branch.branch_name
        )
    else:
        query = query.group_by(
            models.JournalLine.account_id,
            models.Account.name,
            models.Account.account_type
        )
    
    results = query.all()
    
    report_data = {}
    for row in results:
        if group_by == "department":
            group_key = f"{row.dept_name or 'Unassigned'}"
        elif group_by == "branch":
            group_key = f"{row.branch_name or 'Unassigned'}"
        else:
            group_key = "Company Total"
        
        if group_key not in report_data:
            report_data[group_key] = {
                "assets": {},
                "liabilities": {},
                "equity": {},
                "total_assets": 0.0,
                "total_liabilities": 0.0,
                "total_equity": 0.0
            }
        
        balance = float(row.balance)
        if row.account_type == "asset":
            report_data[group_key]["assets"][row.account_name] = balance
            report_data[group_key]["total_assets"] += balance
        elif row.account_type == "liability":
            report_data[group_key]["liabilities"][row.account_name] = balance
            report_data[group_key]["total_liabilities"] += balance
        elif row.account_type == "equity":
            report_data[group_key]["equity"][row.account_name] = balance
            report_data[group_key]["total_equity"] += balance
    
    return {
        "as_of_date": as_of_date,
        "group_by": group_by,
        "report_data": report_data
    }

# Multi-Currency Management Endpoints
@app.get("/api/currencies", response_model=list[schemas.CurrencyResponse])
def get_currencies(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    currencies = db.query(models.Currency).filter(
        models.Currency.company_id == current_user.company_id,
        models.Currency.is_active == True
    ).all()
    return currencies

@app.post("/api/currencies", response_model=schemas.CurrencyResponse)
def create_currency(
    currency: schemas.CurrencyCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Check if currency code already exists for this company
    existing = db.query(models.Currency).filter(
        models.Currency.company_id == current_user.company_id,
        models.Currency.code == currency.code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Currency already exists")
    
    # If this is set as base currency, unset other base currencies
    if currency.is_base_currency:
        db.query(models.Currency).filter(
            models.Currency.company_id == current_user.company_id
        ).update({"is_base_currency": False})
    
    new_currency = models.Currency(
        company_id=current_user.company_id,
        **currency.dict()
    )
    db.add(new_currency)
    db.commit()
    db.refresh(new_currency)
    return new_currency

@app.get("/api/exchange-rates", response_model=list[schemas.ExchangeRateResponse])
def get_exchange_rates(
    from_currency: str = None,
    to_currency: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.ExchangeRate).filter(
        models.ExchangeRate.company_id == current_user.company_id
    )
    
    if from_currency:
        query = query.filter(models.ExchangeRate.from_currency == from_currency)
    if to_currency:
        query = query.filter(models.ExchangeRate.to_currency == to_currency)
    
    rates = query.order_by(models.ExchangeRate.rate_date.desc()).all()
    return rates

@app.post("/api/exchange-rates", response_model=schemas.ExchangeRateResponse)
def create_exchange_rate(
    rate: schemas.ExchangeRateCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    new_rate = models.ExchangeRate(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **rate.dict()
    )
    db.add(new_rate)
    db.commit()
    db.refresh(new_rate)
    return new_rate

@app.get("/api/exchange-rates/latest")
def get_latest_exchange_rate(
    from_currency: str,
    to_currency: str,
    rate_date: date = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get the latest exchange rate for a currency pair as of a specific date"""
    from datetime import date as date_type
    if not rate_date:
        rate_date = date_type.today()
    
    rate = db.query(models.ExchangeRate).filter(
        models.ExchangeRate.company_id == current_user.company_id,
        models.ExchangeRate.from_currency == from_currency,
        models.ExchangeRate.to_currency == to_currency,
        models.ExchangeRate.rate_date <= rate_date
    ).order_by(models.ExchangeRate.rate_date.desc()).first()
    
    if not rate:
        raise HTTPException(
            status_code=404,
            detail=f"No exchange rate found for {from_currency}/{to_currency}"
        )
    
    return {
        "from_currency": rate.from_currency,
        "to_currency": rate.to_currency,
        "rate": rate.rate,
        "rate_date": rate.rate_date,
        "rate_type": rate.rate_type
    }

@app.post("/api/fx-revaluation/execute", response_model=schemas.FXRevaluationResponse)
def execute_fx_revaluation(
    request: schemas.FXRevaluationRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Execute foreign exchange revaluation for accounts in a specific currency"""
    from sqlalchemy import func
    
    # Get base currency
    base_currency_obj = db.query(models.Currency).filter(
        models.Currency.company_id == current_user.company_id,
        models.Currency.is_base_currency == True
    ).first()
    
    if not base_currency_obj:
        raise HTTPException(status_code=400, detail="No base currency configured")
    
    base_currency = base_currency_obj.code
    
    # Get latest exchange rate for the currency
    latest_rate = db.query(models.ExchangeRate).filter(
        models.ExchangeRate.company_id == current_user.company_id,
        models.ExchangeRate.from_currency == base_currency,
        models.ExchangeRate.to_currency == request.currency,
        models.ExchangeRate.rate_date <= request.revaluation_date
    ).order_by(models.ExchangeRate.rate_date.desc()).first()
    
    if not latest_rate:
        raise HTTPException(
            status_code=404,
            detail=f"No exchange rate found for {base_currency}/{request.currency}"
        )
    
    # Get all accounts in the foreign currency that allow FX revaluation
    fx_accounts = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id,
        models.Account.currency == request.currency,
        models.Account.allow_fx_revaluation == True,
        models.Account.is_active == True
    ).all()
    
    if not fx_accounts:
        raise HTTPException(
            status_code=404,
            detail=f"No accounts found for revaluation in currency {request.currency}"
        )
    
    # Create FX Revaluation record
    revaluation = models.FXRevaluation(
        company_id=current_user.company_id,
        revaluation_date=request.revaluation_date,
        currency=request.currency,
        total_gain_loss=0.0,
        status="draft",
        created_by=current_user.id
    )
    db.add(revaluation)
    db.flush()
    
    total_gain_loss = 0.0
    revaluation_lines = []
    
    # Calculate FX gain/loss for each account
    for account in fx_accounts:
        # Get account balance in foreign currency
        balance_query = db.query(
            func.sum(
                func.case(
                    (models.JournalLine.side == "debit", models.JournalLine.amount),
                    else_=-models.JournalLine.amount
                )
            ).label("balance")
        ).join(
            models.JournalEntry, models.JournalLine.journal_id == models.JournalEntry.id
        ).filter(
            models.JournalLine.account_id == account.id,
            models.JournalEntry.date <= request.revaluation_date,
            models.JournalEntry.status == "posted"
        ).first()
        
        foreign_balance = float(balance_query.balance or 0.0)
        
        if abs(foreign_balance) < 0.01:
            continue
        
        # Get previous exchange rate (find last revaluation or use initial rate)
        prev_revaluation_line = db.query(models.FXRevaluationLine).join(
            models.FXRevaluation, models.FXRevaluationLine.revaluation_id == models.FXRevaluation.id
        ).filter(
            models.FXRevaluation.company_id == current_user.company_id,
            models.FXRevaluation.currency == request.currency,
            models.FXRevaluationLine.account_id == account.id,
            models.FXRevaluation.revaluation_date < request.revaluation_date,
            models.FXRevaluation.status == "posted"
        ).order_by(models.FXRevaluation.revaluation_date.desc()).first()
        
        if prev_revaluation_line:
            old_rate = prev_revaluation_line.exchange_rate_new
        else:
            # Get the first exchange rate before or on revaluation date
            first_rate = db.query(models.ExchangeRate).filter(
                models.ExchangeRate.company_id == current_user.company_id,
                models.ExchangeRate.from_currency == base_currency,
                models.ExchangeRate.to_currency == request.currency,
                models.ExchangeRate.rate_date <= request.revaluation_date
            ).order_by(models.ExchangeRate.rate_date.asc()).first()
            old_rate = first_rate.rate if first_rate else latest_rate.rate
        
        new_rate = latest_rate.rate
        
        # Calculate balances in base currency
        balance_base_old = foreign_balance * old_rate
        balance_base_new = foreign_balance * new_rate
        gain_loss = balance_base_new - balance_base_old
        
        # Create revaluation line
        reval_line = models.FXRevaluationLine(
            revaluation_id=revaluation.id,
            account_id=account.id,
            account_currency=request.currency,
            original_balance=foreign_balance,
            exchange_rate_old=old_rate,
            exchange_rate_new=new_rate,
            balance_base_old=balance_base_old,
            balance_base_new=balance_base_new,
            gain_loss=gain_loss
        )
        db.add(reval_line)
        revaluation_lines.append(reval_line)
        total_gain_loss += gain_loss
    
    revaluation.total_gain_loss = total_gain_loss
    db.commit()
    db.refresh(revaluation)
    
    return revaluation

@app.get("/api/fx-revaluation", response_model=list[schemas.FXRevaluationResponse])
def get_fx_revaluations(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    revaluations = db.query(models.FXRevaluation).filter(
        models.FXRevaluation.company_id == current_user.company_id
    ).order_by(models.FXRevaluation.revaluation_date.desc()).all()
    return revaluations

@app.get("/api/fx-revaluation/{revaluation_id}/lines", response_model=list[schemas.FXRevaluationLineResponse])
def get_revaluation_lines(
    revaluation_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Verify revaluation belongs to user's company
    revaluation = db.query(models.FXRevaluation).filter(
        models.FXRevaluation.id == revaluation_id,
        models.FXRevaluation.company_id == current_user.company_id
    ).first()
    
    if not revaluation:
        raise HTTPException(status_code=404, detail="Revaluation not found")
    
    lines = db.query(models.FXRevaluationLine).filter(
        models.FXRevaluationLine.revaluation_id == revaluation_id
    ).all()
    return lines

@app.post("/api/fx-revaluation/{revaluation_id}/post")
def post_fx_revaluation(
    revaluation_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Post FX revaluation by creating a journal entry for the gain/loss"""
    revaluation = db.query(models.FXRevaluation).filter(
        models.FXRevaluation.id == revaluation_id,
        models.FXRevaluation.company_id == current_user.company_id
    ).first()
    
    if not revaluation:
        raise HTTPException(status_code=404, detail="Revaluation not found")
    
    if revaluation.status == "posted":
        raise HTTPException(status_code=400, detail="Revaluation already posted")
    
    # Get FX gain/loss accounts
    fx_gain_account = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id,
        models.Account.code == "7100",  # FX Gain
        models.Account.is_active == True
    ).first()
    
    fx_loss_account = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id,
        models.Account.code == "8100",  # FX Loss
        models.Account.is_active == True
    ).first()
    
    if not fx_gain_account or not fx_loss_account:
        raise HTTPException(
            status_code=400,
            detail="FX Gain (7100) or FX Loss (8100) accounts not configured"
        )
    
    # Create journal entry
    journal_count = db.query(models.JournalEntry).filter(
        models.JournalEntry.company_id == current_user.company_id
    ).count()
    journal_number = f"JE-{journal_count + 1:06d}"
    
    journal = models.JournalEntry(
        company_id=current_user.company_id,
        journal_number=journal_number,
        date=revaluation.revaluation_date,
        description=f"FX Revaluation - {revaluation.currency}",
        currency=db.query(models.Company).filter(
            models.Company.id == current_user.company_id
        ).first().currency,
        total_amount=abs(revaluation.total_gain_loss),
        status="posted",
        created_by=current_user.id
    )
    db.add(journal)
    db.flush()
    
    # Get revaluation lines
    lines = db.query(models.FXRevaluationLine).filter(
        models.FXRevaluationLine.revaluation_id == revaluation_id
    ).all()
    
    # Create journal lines for each account
    for line in lines:
        if abs(line.gain_loss) < 0.01:
            continue
        
        # Post to account
        account_line = models.JournalLine(
            journal_id=journal.id,
            account_id=line.account_id,
            description=f"FX Revaluation - {line.account_currency}",
            amount=abs(line.gain_loss),
            side="debit" if line.gain_loss > 0 else "credit"
        )
        db.add(account_line)
        
        # Post to FX gain/loss
        fx_line = models.JournalLine(
            journal_id=journal.id,
            account_id=fx_gain_account.id if line.gain_loss > 0 else fx_loss_account.id,
            description=f"FX Revaluation - {line.account_currency}",
            amount=abs(line.gain_loss),
            side="credit" if line.gain_loss > 0 else "debit"
        )
        db.add(fx_line)
    
    revaluation.journal_entry_id = journal.id
    revaluation.status = "posted"
    
    db.commit()
    
    return {"message": "FX Revaluation posted successfully", "journal_number": journal_number}

# Bank Reconciliation Endpoints
@app.post("/api/bank-accounts", response_model=schemas.BankAccountResponse)
def create_bank_account(
    bank_account: schemas.BankAccountCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Validate account belongs to company
    account = db.query(models.Account).filter(
        models.Account.id == bank_account.account_id,
        models.Account.company_id == current_user.company_id
    ).first()
    if not account:
        raise HTTPException(status_code=400, detail="Invalid account")
    
    new_bank_account = models.BankAccount(
        company_id=current_user.company_id,
        **bank_account.dict()
    )
    db.add(new_bank_account)
    db.commit()
    db.refresh(new_bank_account)
    return new_bank_account

@app.get("/api/bank-accounts", response_model=list[schemas.BankAccountResponse])
def get_bank_accounts(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    accounts = db.query(models.BankAccount).filter(
        models.BankAccount.company_id == current_user.company_id,
        models.BankAccount.is_active == True
    ).all()
    return accounts

@app.post("/api/bank-statements", response_model=schemas.BankStatementResponse)
def import_bank_statement(
    statement: schemas.BankStatementCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Validate bank account belongs to company
    bank_account = db.query(models.BankAccount).filter(
        models.BankAccount.id == statement.bank_account_id,
        models.BankAccount.company_id == current_user.company_id
    ).first()
    if not bank_account:
        raise HTTPException(status_code=400, detail="Invalid bank account")
    
    new_statement = models.BankStatement(
        company_id=current_user.company_id,
        bank_account_id=statement.bank_account_id,
        statement_number=statement.statement_number,
        statement_date=statement.statement_date,
        opening_balance=statement.opening_balance,
        closing_balance=statement.closing_balance,
        status="imported",
        import_source="manual",
        created_by=current_user.id
    )
    db.add(new_statement)
    db.flush()
    
    # Add statement lines
    for line_data in statement.lines:
        line = models.BankStatementLine(
            statement_id=new_statement.id,
            **line_data.dict()
        )
        db.add(line)
    
    db.commit()
    db.refresh(new_statement)
    return new_statement

@app.post("/api/bank-reconciliation/auto-match/{statement_id}")
def auto_match_statement(
    statement_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Auto-match bank statement lines with journal entries"""
    from sqlalchemy import and_, or_
    
    # Verify statement belongs to company
    statement = db.query(models.BankStatement).filter(
        models.BankStatement.id == statement_id,
        models.BankStatement.company_id == current_user.company_id
    ).first()
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    
    # Get bank account
    bank_account = db.query(models.BankAccount).filter(
        models.BankAccount.id == statement.bank_account_id
    ).first()
    
    # Get unmatched statement lines
    unmatched_lines = db.query(models.BankStatementLine).filter(
        models.BankStatementLine.statement_id == statement_id,
        models.BankStatementLine.is_matched == False
    ).all()
    
    matches_found = 0
    
    for stmt_line in unmatched_lines:
        # Get amount to match (debit or credit)
        amount_to_match = stmt_line.debit if stmt_line.debit > 0 else stmt_line.credit
        side_to_match = "debit" if stmt_line.debit > 0 else "credit"
        
        # Find matching journal lines
        # Match by: same amount, same date (±3 days), same account, not already matched
        potential_matches = db.query(models.JournalLine).join(
            models.JournalEntry, models.JournalLine.journal_id == models.JournalEntry.id
        ).filter(
            models.JournalEntry.company_id == current_user.company_id,
            models.JournalLine.account_id == bank_account.account_id,
            models.JournalLine.amount == amount_to_match,
            models.JournalLine.side == side_to_match,
            models.JournalEntry.date >= stmt_line.transaction_date - timedelta(days=3),
            models.JournalEntry.date <= stmt_line.transaction_date + timedelta(days=3),
            models.JournalEntry.status == "posted"
        ).all()
        
        # Check which ones are not already matched
        for journal_line in potential_matches:
            already_matched = db.query(models.BankReconciliationMatch).filter(
                models.BankReconciliationMatch.journal_line_id == journal_line.id
            ).first()
            
            if not already_matched:
                # Create match
                stmt_line.is_matched = True
                stmt_line.matched_journal_line_id = journal_line.id
                matches_found += 1
                break
    
    db.commit()
    
    return {
        "message": f"Auto-matching complete. {matches_found} matches found.",
        "matches_found": matches_found,
        "total_lines": len(unmatched_lines)
    }

# Fixed Assets Endpoints
@app.post("/api/fixed-assets")
def create_fixed_asset(
    asset: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Validate accounts belong to company
    for account_field in ['asset_account_id', 'depreciation_account_id', 'accumulated_depreciation_account_id']:
        if account_field in asset and asset[account_field]:
            acc = db.query(models.Account).filter(
                models.Account.id == asset[account_field],
                models.Account.company_id == current_user.company_id
            ).first()
            if not acc:
                raise HTTPException(status_code=400, detail=f"Invalid {account_field}")
    
    new_asset = models.FixedAsset(
        company_id=current_user.company_id,
        **asset
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    return new_asset

@app.get("/api/fixed-assets")
def get_fixed_assets(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    assets = db.query(models.FixedAsset).filter(
        models.FixedAsset.company_id == current_user.company_id
    ).all()
    return assets

@app.post("/api/fixed-assets/{asset_id}/depreciate")
def calculate_depreciation(
    asset_id: str,
    period_month: int,
    period_year: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate and post depreciation for an asset for a specific period"""
    asset = db.query(models.FixedAsset).filter(
        models.FixedAsset.id == asset_id,
        models.FixedAsset.company_id == current_user.company_id
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Calculate depreciation based on method
    if asset.depreciation_method == "straight_line":
        monthly_depreciation = (asset.purchase_cost - asset.residual_value) / (asset.useful_life_years * 12)
    else:  # reducing_balance
        annual_rate = asset.depreciation_rate if asset.depreciation_rate else (1 / asset.useful_life_years)
        monthly_rate = annual_rate / 12
        current_book_value = asset.purchase_cost - asset.accumulated_depreciation
        monthly_depreciation = current_book_value * monthly_rate
    
    # Create depreciation schedule entry
    schedule = models.DepreciationSchedule(
        asset_id=asset_id,
        period_month=period_month,
        period_year=period_year,
        opening_book_value=asset.purchase_cost - asset.accumulated_depreciation,
        depreciation_amount=monthly_depreciation,
        closing_book_value=asset.purchase_cost - asset.accumulated_depreciation - monthly_depreciation,
        status="posted"
    )
    db.add(schedule)
    
    # Update asset accumulated depreciation
    asset.accumulated_depreciation += monthly_depreciation
    asset.book_value = asset.purchase_cost - asset.accumulated_depreciation
    
    db.commit()
    return {"message": "Depreciation calculated", "amount": monthly_depreciation}

# Smart Invoice Endpoints
@app.post("/api/invoices")
def create_invoice(
    invoice: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Validate customer belongs to company
    customer = db.query(models.Customer).filter(
        models.Customer.id == invoice['customer_id'],
        models.Customer.company_id == current_user.company_id
    ).first()
    if not customer:
        raise HTTPException(status_code=400, detail="Invalid customer")
    
    # Generate invoice number
    invoice_count = db.query(models.Invoice).filter(
        models.Invoice.company_id == current_user.company_id
    ).count()
    invoice_number = f"INV-{invoice_count + 1:06d}"
    
    # Generate QR code for ZRA compliance (placeholder)
    import json
    qr_data = json.dumps({
        "invoice_number": invoice_number,
        "customer": customer.name,
        "amount": invoice.get('total_amount', 0),
        "date": str(invoice.get('invoice_date'))
    })
    
    new_invoice = models.Invoice(
        company_id=current_user.company_id,
        invoice_number=invoice_number,
        customer_id=invoice['customer_id'],
        invoice_date=invoice['invoice_date'],
        due_date=invoice['due_date'],
        currency=invoice.get('currency', 'ZMW'),
        subtotal=invoice['subtotal'],
        tax_amount=invoice.get('tax_amount', 0.0),
        total_amount=invoice['total_amount'],
        qr_code=qr_data,
        status="draft",
        created_by=current_user.id
    )
    db.add(new_invoice)
    db.flush()
    
    # Add invoice lines
    if 'lines' in invoice:
        for line_data in invoice['lines']:
            line = models.InvoiceLine(
                invoice_id=new_invoice.id,
                **line_data
            )
            db.add(line)
    
    db.commit()
    db.refresh(new_invoice)
    return new_invoice

@app.get("/api/invoices")
def get_invoices(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    invoices = db.query(models.Invoice).filter(
        models.Invoice.company_id == current_user.company_id
    ).order_by(models.Invoice.invoice_date.desc()).all()
    return invoices

@app.post("/api/invoices/{invoice_id}/zra-validate")
def validate_with_zra(
    invoice_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Validate invoice with ZRA (placeholder for actual ZRA API integration)"""
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.company_id == current_user.company_id
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Placeholder: In production, integrate with actual ZRA API
    invoice.zra_validated = True
    invoice.zra_validated_at = datetime.utcnow()
    invoice.zra_reference = f"ZRA-{invoice.invoice_number}-{int(datetime.utcnow().timestamp())}"
    
    db.commit()
    return {"message": "Invoice validated with ZRA", "zra_reference": invoice.zra_reference}

# Accounting Period Endpoints
@app.post("/api/accounting-periods")
def create_accounting_period(
    period: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    new_period = models.AccountingPeriod(
        company_id=current_user.company_id,
        **period
    )
    db.add(new_period)
    db.commit()
    db.refresh(new_period)
    return new_period

@app.get("/api/accounting-periods")
def get_accounting_periods(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    periods = db.query(models.AccountingPeriod).filter(
        models.AccountingPeriod.company_id == current_user.company_id
    ).order_by(models.AccountingPeriod.start_date.desc()).all()
    return periods

@app.post("/api/accounting-periods/{period_id}/close")
def close_accounting_period(
    period_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Close an accounting period (prevents new transactions)"""
    period = db.query(models.AccountingPeriod).filter(
        models.AccountingPeriod.id == period_id,
        models.AccountingPeriod.company_id == current_user.company_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    if period.is_closed:
        raise HTTPException(status_code=400, detail="Period already closed")
    
    period.is_closed = True
    period.closed_at = datetime.utcnow()
    period.closed_by = current_user.id
    
    db.commit()
    return {"message": f"Period {period.period_name} closed successfully"}

@app.post("/api/accounting-periods/{period_id}/lock")
def lock_accounting_period(
    period_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Lock an accounting period (prevents any edits, including adjustments)"""
    period = db.query(models.AccountingPeriod).filter(
        models.AccountingPeriod.id == period_id,
        models.AccountingPeriod.company_id == current_user.company_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    if not period.is_closed:
        raise HTTPException(status_code=400, detail="Period must be closed before locking")
    
    if period.is_locked:
        raise HTTPException(status_code=400, detail="Period already locked")
    
    period.is_locked = True
    period.locked_at = datetime.utcnow()
    period.locked_by = current_user.id
    
    db.commit()
    return {"message": f"Period {period.period_name} locked successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

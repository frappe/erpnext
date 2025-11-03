from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
import os
import uuid
import models
import schemas
import auth
import utils
from database import engine, get_db
from ai_assistant import ai_assistant
from notification_service import notification_service
from audit_logger import audit_logger
import migrations
from routers import bank_connections

models.Base.metadata.create_all(bind=engine)
migrations.run_migrations()

app = FastAPI(title="ERIK ERP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bank_connections.router)

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
def login(user: schemas.UserLogin, request: Request, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    
    if not db_user:
        audit_logger.log_login_attempt(
            db=db,
            email=user.email,
            request=request,
            status="failure",
            error_message="Unknown user account"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not auth.verify_password(user.password, db_user.hashed_password):
        audit_logger.log_login(
            db=db,
            user=db_user,
            request=request,
            status="failure",
            error_message="Incorrect password"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    db_user.last_login = datetime.utcnow()
    db.commit()
    
    audit_logger.log_login(db=db, user=db_user, request=request, status="success")
    
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
    request: Request,
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
    
    audit_logger.log_create(
        db=db,
        user=current_user,
        entity_type="Employee",
        entity_id=new_employee.id,
        data={
            "employee_no": new_employee.employee_no,
            "name": f"{new_employee.first_name} {new_employee.last_name}",
            "position": new_employee.position,
            "salary_base": new_employee.salary_base
        },
        request=request
    )
    
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

# Operations & Batch Tracking Endpoints
@app.post("/api/operations")
def create_operation(
    operation: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new operation template (for manufacturing, agriculture, etc.)"""
    # Validate department if provided
    if 'department_id' in operation and operation['department_id']:
        dept = db.query(models.Department).filter(
            models.Department.id == operation['department_id'],
            models.Department.company_id == current_user.company_id
        ).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid department")
    
    # Validate output product if provided
    if 'output_product_id' in operation and operation['output_product_id']:
        product = db.query(models.Product).filter(
            models.Product.id == operation['output_product_id'],
            models.Product.company_id == current_user.company_id
        ).first()
        if not product:
            raise HTTPException(status_code=400, detail="Invalid output product")
    
    # Extract steps before creating operation (avoid passing nested dict to model)
    steps_data = operation.pop('steps', [])
    
    new_operation = models.Operation(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **operation
    )
    db.add(new_operation)
    db.flush()
    
    # Add operation steps if provided
    for step_data in steps_data:
        step = models.OperationStep(
            operation_id=new_operation.id,
            **step_data
        )
        db.add(step)
    
    db.commit()
    db.refresh(new_operation)
    return new_operation

@app.get("/api/operations")
def get_operations(
    operation_type: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all operations for the company, optionally filtered by type"""
    query = db.query(models.Operation).filter(
        models.Operation.company_id == current_user.company_id
    )
    
    if operation_type:
        query = query.filter(models.Operation.operation_type == operation_type)
    
    operations = query.all()
    return operations

@app.post("/api/batches")
def create_batch(
    batch: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new production batch"""
    # Validate operation
    operation = db.query(models.Operation).filter(
        models.Operation.id == batch['operation_id'],
        models.Operation.company_id == current_user.company_id
    ).first()
    if not operation:
        raise HTTPException(status_code=400, detail="Invalid operation")
    
    # Validate department if provided
    if 'department_id' in batch and batch['department_id']:
        dept = db.query(models.Department).filter(
            models.Department.id == batch['department_id'],
            models.Department.company_id == current_user.company_id
        ).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid department")
    
    # Validate branch if provided
    if 'branch_id' in batch and batch['branch_id']:
        branch = db.query(models.Branch).filter(
            models.Branch.id == batch['branch_id'],
            models.Branch.company_id == current_user.company_id
        ).first()
        if not branch:
            raise HTTPException(status_code=400, detail="Invalid branch")
    
    # Generate batch number
    batch_count = db.query(models.Batch).filter(
        models.Batch.company_id == current_user.company_id
    ).count()
    batch_number = f"BATCH-{batch_count + 1:06d}"
    
    new_batch = models.Batch(
        company_id=current_user.company_id,
        batch_number=batch_number,
        created_by=current_user.id,
        **batch
    )
    db.add(new_batch)
    db.flush()
    
    # Add inputs if provided
    if 'inputs' in batch:
        for input_data in batch['inputs']:
            batch_input = models.BatchInput(
                batch_id=new_batch.id,
                **input_data
            )
            db.add(batch_input)
    
    db.commit()
    db.refresh(new_batch)
    return new_batch

@app.get("/api/batches")
def get_batches(
    status: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all batches for the company, optionally filtered by status"""
    query = db.query(models.Batch).filter(
        models.Batch.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.Batch.status == status)
    
    batches = query.order_by(models.Batch.created_at.desc()).all()
    return batches

@app.post("/api/batches/{batch_id}/start")
def start_batch(
    batch_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Start a batch (change status to in_progress)"""
    batch = db.query(models.Batch).filter(
        models.Batch.id == batch_id,
        models.Batch.company_id == current_user.company_id
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    if batch.status not in ['draft', 'planned']:
        raise HTTPException(status_code=400, detail="Batch cannot be started")
    
    batch.status = "in_progress"
    batch.start_date = datetime.utcnow()
    
    db.commit()
    return {"message": f"Batch {batch.batch_number} started"}

@app.post("/api/batches/{batch_id}/complete")
def complete_batch(
    batch_id: str,
    actual_quantity: float,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Complete a batch and calculate costs"""
    batch = db.query(models.Batch).filter(
        models.Batch.id == batch_id,
        models.Batch.company_id == current_user.company_id
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    if batch.status != "in_progress":
        raise HTTPException(status_code=400, detail="Batch must be in progress")
    
    batch.status = "completed"
    batch.actual_quantity = actual_quantity
    batch.actual_end_date = datetime.utcnow()
    
    # Calculate total costs
    total_material_cost = db.query(func.sum(models.BatchInput.total_cost)).filter(
        models.BatchInput.batch_id == batch_id
    ).scalar() or 0.0
    
    total_other_costs = db.query(func.sum(models.BatchCost.amount)).filter(
        models.BatchCost.batch_id == batch_id
    ).scalar() or 0.0
    
    total_cost = total_material_cost + total_other_costs
    unit_cost = total_cost / actual_quantity if actual_quantity > 0 else 0
    
    db.commit()
    
    return {
        "message": f"Batch {batch.batch_number} completed",
        "actual_quantity": actual_quantity,
        "total_cost": total_cost,
        "unit_cost": unit_cost
    }

@app.post("/api/batches/{batch_id}/inputs")
def add_batch_input(
    batch_id: str,
    input_data: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Add material input to a batch"""
    batch = db.query(models.Batch).filter(
        models.Batch.id == batch_id,
        models.Batch.company_id == current_user.company_id
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Validate product
    product = db.query(models.Product).filter(
        models.Product.id == input_data['product_id'],
        models.Product.company_id == current_user.company_id
    ).first()
    if not product:
        raise HTTPException(status_code=400, detail="Invalid product")
    
    batch_input = models.BatchInput(
        batch_id=batch_id,
        issued_at=datetime.utcnow(),
        **input_data
    )
    db.add(batch_input)
    db.commit()
    db.refresh(batch_input)
    return batch_input

@app.post("/api/batches/{batch_id}/outputs")
def add_batch_output(
    batch_id: str,
    output_data: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Record output from a batch"""
    batch = db.query(models.Batch).filter(
        models.Batch.id == batch_id,
        models.Batch.company_id == current_user.company_id
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Validate product
    product = db.query(models.Product).filter(
        models.Product.id == output_data['product_id'],
        models.Product.company_id == current_user.company_id
    ).first()
    if not product:
        raise HTTPException(status_code=400, detail="Invalid product")
    
    batch_output = models.BatchOutput(
        batch_id=batch_id,
        received_at=datetime.utcnow(),
        **output_data
    )
    db.add(batch_output)
    db.commit()
    db.refresh(batch_output)
    return batch_output

@app.post("/api/batches/{batch_id}/costs")
def add_batch_cost(
    batch_id: str,
    cost_data: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Add a cost entry to a batch (labor, overhead, etc.)"""
    batch = db.query(models.Batch).filter(
        models.Batch.id == batch_id,
        models.Batch.company_id == current_user.company_id
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch_cost = models.BatchCost(
        batch_id=batch_id,
        **cost_data
    )
    db.add(batch_cost)
    db.commit()
    db.refresh(batch_cost)
    return batch_cost

# Transfer Pricing Endpoints
@app.post("/api/transfer-prices")
def create_transfer_price(
    price_data: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Define transfer pricing rules between departments/branches"""
    # Validate product
    product = db.query(models.Product).filter(
        models.Product.id == price_data['product_id'],
        models.Product.company_id == current_user.company_id
    ).first()
    if not product:
        raise HTTPException(status_code=400, detail="Invalid product")
    
    # Validate departments/branches if provided
    for field, model in [
        ('from_department_id', models.Department),
        ('to_department_id', models.Department),
        ('from_branch_id', models.Branch),
        ('to_branch_id', models.Branch)
    ]:
        if field in price_data and price_data[field]:
            entity = db.query(model).filter(
                model.id == price_data[field],
                model.company_id == current_user.company_id
            ).first()
            if not entity:
                raise HTTPException(status_code=400, detail=f"Invalid {field}")
    
    # Calculate margin if cost_plus method
    if price_data.get('pricing_method') == 'cost_plus':
        cost = price_data.get('cost_price', 0.0)
        markup = price_data.get('markup_percentage', 0.0)
        transfer_price = cost * (1 + markup / 100)
        price_data['transfer_price'] = transfer_price
        price_data['margin_amount'] = transfer_price - cost
        price_data['margin_percentage'] = markup
    
    new_price = models.TransferPrice(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **price_data
    )
    db.add(new_price)
    db.commit()
    db.refresh(new_price)
    return new_price

@app.get("/api/transfer-prices")
def get_transfer_prices(
    product_id: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get transfer pricing rules"""
    query = db.query(models.TransferPrice).filter(
        models.TransferPrice.company_id == current_user.company_id,
        models.TransferPrice.is_active == True
    )
    
    if product_id:
        query = query.filter(models.TransferPrice.product_id == product_id)
    
    prices = query.all()
    return prices

@app.post("/api/transfer-orders")
def create_transfer_order(
    order_data: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create an inter-department/inter-branch transfer order"""
    # Validate departments/branches
    for field, model in [
        ('from_department_id', models.Department),
        ('to_department_id', models.Department),
        ('from_branch_id', models.Branch),
        ('to_branch_id', models.Branch),
        ('from_warehouse_id', models.Warehouse),
        ('to_warehouse_id', models.Warehouse)
    ]:
        if field in order_data and order_data[field]:
            entity = db.query(model).filter(
                model.id == order_data[field],
                model.company_id == current_user.company_id
            ).first()
            if not entity:
                raise HTTPException(status_code=400, detail=f"Invalid {field}")
    
    # Generate transfer number
    transfer_count = db.query(models.TransferOrder).filter(
        models.TransferOrder.company_id == current_user.company_id
    ).count()
    transfer_number = f"TRF-{transfer_count + 1:06d}"
    
    new_order = models.TransferOrder(
        company_id=current_user.company_id,
        transfer_number=transfer_number,
        created_by=current_user.id,
        transfer_date=order_data['transfer_date'],
        from_department_id=order_data.get('from_department_id'),
        to_department_id=order_data.get('to_department_id'),
        from_branch_id=order_data.get('from_branch_id'),
        to_branch_id=order_data.get('to_branch_id'),
        from_warehouse_id=order_data.get('from_warehouse_id'),
        to_warehouse_id=order_data.get('to_warehouse_id'),
        notes=order_data.get('notes')
    )
    db.add(new_order)
    db.flush()
    
    # Add lines with transfer pricing
    total_cost = 0.0
    total_price = 0.0
    
    if 'lines' in order_data:
        for line_data in order_data['lines']:
            # Validate product
            product = db.query(models.Product).filter(
                models.Product.id == line_data['product_id'],
                models.Product.company_id == current_user.company_id
            ).first()
            if not product:
                raise HTTPException(status_code=400, detail="Invalid product in line items")
            
            # Get transfer price
            transfer_price_rule = db.query(models.TransferPrice).filter(
                models.TransferPrice.company_id == current_user.company_id,
                models.TransferPrice.product_id == line_data['product_id'],
                models.TransferPrice.is_active == True
            ).first()
            
            unit_cost = line_data.get('unit_cost', product.cost if hasattr(product, 'cost') else 0.0)
            transfer_price = transfer_price_rule.transfer_price if transfer_price_rule else unit_cost
            quantity = line_data['quantity']
            
            line_total_cost = unit_cost * quantity
            line_total_price = transfer_price * quantity
            margin = line_total_price - line_total_cost
            margin_pct = (margin / line_total_cost * 100) if line_total_cost > 0 else 0
            
            line = models.TransferOrderLine(
                transfer_order_id=new_order.id,
                product_id=line_data['product_id'],
                quantity=quantity,
                unit_cost=unit_cost,
                transfer_price=transfer_price,
                margin_amount=margin,
                margin_percentage=margin_pct,
                line_total_cost=line_total_cost,
                line_total_price=line_total_price
            )
            db.add(line)
            
            total_cost += line_total_cost
            total_price += line_total_price
    
    new_order.total_cost = total_cost
    new_order.total_transfer_price = total_price
    new_order.total_margin = total_price - total_cost
    
    db.commit()
    db.refresh(new_order)
    return new_order

@app.get("/api/transfer-orders")
def get_transfer_orders(
    status: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get transfer orders"""
    query = db.query(models.TransferOrder).filter(
        models.TransferOrder.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.TransferOrder.status == status)
    
    orders = query.order_by(models.TransferOrder.transfer_date.desc()).all()
    return orders

@app.post("/api/transfer-orders/{order_id}/approve")
def approve_transfer_order(
    order_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Approve a transfer order"""
    order = db.query(models.TransferOrder).filter(
        models.TransferOrder.id == order_id,
        models.TransferOrder.company_id == current_user.company_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Transfer order not found")
    
    if order.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft orders can be approved")
    
    order.status = "approved"
    order.approved_by = current_user.id
    order.approved_at = datetime.utcnow()
    
    db.commit()
    return {"message": f"Transfer order {order.transfer_number} approved"}

@app.post("/api/transfer-orders/{order_id}/receive")
def receive_transfer_order(
    order_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Mark transfer order as received"""
    order = db.query(models.TransferOrder).filter(
        models.TransferOrder.id == order_id,
        models.TransferOrder.company_id == current_user.company_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Transfer order not found")
    
    if order.status not in ["approved", "in_transit"]:
        raise HTTPException(status_code=400, detail="Order must be approved or in transit")
    
    order.status = "received"
    order.received_by = current_user.id
    order.received_at = datetime.utcnow()
    
    db.commit()
    return {"message": f"Transfer order {order.transfer_number} received"}

# WIP (Work-In-Progress) Tracking Endpoints
@app.get("/api/wip-balances")
def get_wip_balances(
    department_id: str = None,
    branch_id: str = None,
    product_id: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get Work-In-Progress balances (calculated from in-progress batches)"""
    # Query in-progress batches
    query = db.query(models.Batch).filter(
        models.Batch.company_id == current_user.company_id,
        models.Batch.status.in_(['planned', 'in_progress'])
    )
    
    if department_id:
        query = query.filter(models.Batch.department_id == department_id)
    if branch_id:
        query = query.filter(models.Batch.branch_id == branch_id)
    
    batches = query.all()
    
    # Calculate WIP by product
    wip_summary = {}
    
    for batch in batches:
        # Calculate material costs from inputs
        material_cost = db.query(func.sum(models.BatchInput.total_cost)).filter(
            models.BatchInput.batch_id == batch.id
        ).scalar() or 0.0
        
        # Calculate other costs (labor, overhead, machine)
        labor_cost = db.query(func.sum(models.BatchCost.amount)).filter(
            models.BatchCost.batch_id == batch.id,
            models.BatchCost.cost_type == 'labor'
        ).scalar() or 0.0
        
        overhead_cost = db.query(func.sum(models.BatchCost.amount)).filter(
            models.BatchCost.batch_id == batch.id,
            models.BatchCost.cost_type == 'overhead'
        ).scalar() or 0.0
        
        machine_cost = db.query(func.sum(models.BatchCost.amount)).filter(
            models.BatchCost.batch_id == batch.id,
            models.BatchCost.cost_type == 'machine'
        ).scalar() or 0.0
        
        total_cost = material_cost + labor_cost + overhead_cost + machine_cost
        
        # Get operation details
        operation = db.query(models.Operation).filter(
            models.Operation.id == batch.operation_id
        ).first()
        
        product_id_key = operation.output_product_id if operation else None
        
        if product_id_key:
            if product_id_key not in wip_summary:
                wip_summary[product_id_key] = {
                    'product_id': product_id_key,
                    'material_cost': 0.0,
                    'labor_cost': 0.0,
                    'overhead_cost': 0.0,
                    'machine_cost': 0.0,
                    'total_wip_value': 0.0,
                    'quantity_in_progress': 0.0,
                    'batch_count': 0
                }
            
            wip_summary[product_id_key]['material_cost'] += material_cost
            wip_summary[product_id_key]['labor_cost'] += labor_cost
            wip_summary[product_id_key]['overhead_cost'] += overhead_cost
            wip_summary[product_id_key]['machine_cost'] += machine_cost
            wip_summary[product_id_key]['total_wip_value'] += total_cost
            wip_summary[product_id_key]['quantity_in_progress'] += batch.planned_quantity
            wip_summary[product_id_key]['batch_count'] += 1
    
    return list(wip_summary.values())

@app.post("/api/wip-balances/snapshot")
def create_wip_snapshot(
    as_of_date: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a WIP balance snapshot for reporting purposes"""
    from datetime import datetime as dt
    snapshot_date = dt.fromisoformat(as_of_date).date()
    
    # Query in-progress batches
    batches = db.query(models.Batch).filter(
        models.Batch.company_id == current_user.company_id,
        models.Batch.status.in_(['planned', 'in_progress'])
    ).all()
    
    snapshots_created = 0
    
    for batch in batches:
        # Calculate costs
        material_cost = db.query(func.sum(models.BatchInput.total_cost)).filter(
            models.BatchInput.batch_id == batch.id
        ).scalar() or 0.0
        
        labor_cost = db.query(func.sum(models.BatchCost.amount)).filter(
            models.BatchCost.batch_id == batch.id,
            models.BatchCost.cost_type == 'labor'
        ).scalar() or 0.0
        
        overhead_cost = db.query(func.sum(models.BatchCost.amount)).filter(
            models.BatchCost.batch_id == batch.id,
            models.BatchCost.cost_type == 'overhead'
        ).scalar() or 0.0
        
        machine_cost = db.query(func.sum(models.BatchCost.amount)).filter(
            models.BatchCost.batch_id == batch.id,
            models.BatchCost.cost_type == 'machine'
        ).scalar() or 0.0
        
        total_cost = material_cost + labor_cost + overhead_cost + machine_cost
        
        if total_cost > 0:
            operation = db.query(models.Operation).filter(
                models.Operation.id == batch.operation_id
            ).first()
            
            snapshot = models.WIPBalance(
                company_id=current_user.company_id,
                product_id=operation.output_product_id if operation else None,
                operation_id=batch.operation_id,
                department_id=batch.department_id,
                branch_id=batch.branch_id,
                as_of_date=snapshot_date,
                material_cost=material_cost,
                labor_cost=labor_cost,
                overhead_cost=overhead_cost,
                machine_cost=machine_cost,
                total_wip_value=total_cost,
                quantity_in_progress=batch.planned_quantity,
                batch_count=1
            )
            db.add(snapshot)
            snapshots_created += 1
    
    db.commit()
    return {
        "message": f"WIP snapshot created for {snapshot_date}",
        "snapshots_created": snapshots_created
    }

@app.get("/api/wip-balances/history")
def get_wip_history(
    start_date: str = None,
    end_date: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get historical WIP balance snapshots"""
    query = db.query(models.WIPBalance).filter(
        models.WIPBalance.company_id == current_user.company_id
    )
    
    if start_date:
        from datetime import datetime as dt
        query = query.filter(models.WIPBalance.as_of_date >= dt.fromisoformat(start_date).date())
    if end_date:
        from datetime import datetime as dt
        query = query.filter(models.WIPBalance.as_of_date <= dt.fromisoformat(end_date).date())
    
    snapshots = query.order_by(models.WIPBalance.as_of_date.desc()).all()
    return snapshots

# Industry Templates Endpoints
@app.post("/api/industry-templates/seed")
def seed_industry_templates(db: Session = Depends(get_db)):
    """Seed default industry templates (Agriculture, Manufacturing, Retail)"""
    templates = [
        {
            "template_code": "AGRICULTURE",
            "template_name": "Agriculture & Farming",
            "industry_type": "agriculture",
            "description": "Template for agricultural businesses including crop cultivation, livestock, and harvest tracking",
            "template_config": {
                "operations": [
                    {
                        "operation_code": "CROP-PLANT",
                        "operation_name": "Crop Planting",
                        "operation_type": "agriculture",
                        "description": "Planting seeds/seedlings for crop cultivation",
                        "steps": [
                            {"step_number": 1, "step_name": "Land Preparation", "duration_hours": 8},
                            {"step_number": 2, "step_name": "Seed Planting", "duration_hours": 6},
                            {"step_number": 3, "step_name": "Initial Irrigation", "duration_hours": 2}
                        ]
                    },
                    {
                        "operation_code": "CROP-HARVEST",
                        "operation_name": "Crop Harvesting",
                        "operation_type": "agriculture",
                        "description": "Harvesting mature crops",
                        "steps": [
                            {"step_number": 1, "step_name": "Harvest Collection", "duration_hours": 10},
                            {"step_number": 2, "step_name": "Quality Sorting", "duration_hours": 4, "is_quality_control": True},
                            {"step_number": 3, "step_name": "Storage/Packaging", "duration_hours": 3}
                        ]
                    },
                    {
                        "operation_code": "LIVESTOCK-FEED",
                        "operation_name": "Livestock Feeding & Care",
                        "operation_type": "agriculture",
                        "description": "Daily feeding and care for livestock"
                    }
                ],
                "product_categories": ["Seeds", "Fertilizers", "Crops - Maize", "Crops - Wheat", "Livestock", "Dairy Products"],
                "recommended_accounts": [
                    {"account_code": "1510", "account_name": "Growing Crops (Biological Assets)", "account_type": "asset"},
                    {"account_code": "1520", "account_name": "Livestock (Biological Assets)", "account_type": "asset"},
                    {"account_code": "5110", "account_name": "Crop Production Costs", "account_type": "expense"}
                ]
            }
        },
        {
            "template_code": "MANUFACTURING",
            "template_name": "Manufacturing & Production",
            "industry_type": "manufacturing",
            "description": "Template for manufacturing businesses with production lines, assembly, and quality control",
            "template_config": {
                "operations": [
                    {
                        "operation_code": "ASSEMBLY-LINE",
                        "operation_name": "Assembly Line Production",
                        "operation_type": "manufacturing",
                        "description": "Standard assembly line manufacturing process",
                        "steps": [
                            {"step_number": 1, "step_name": "Component Preparation", "duration_hours": 2},
                            {"step_number": 2, "step_name": "Assembly", "duration_hours": 4},
                            {"step_number": 3, "step_name": "Quality Inspection", "duration_hours": 1, "is_quality_control": True},
                            {"step_number": 4, "step_name": "Packaging", "duration_hours": 1}
                        ]
                    },
                    {
                        "operation_code": "MACHINING",
                        "operation_name": "CNC Machining",
                        "operation_type": "manufacturing",
                        "description": "Precision machining operations",
                        "steps": [
                            {"step_number": 1, "step_name": "Material Setup", "duration_hours": 0.5},
                            {"step_number": 2, "step_name": "CNC Machining", "duration_hours": 3},
                            {"step_number": 3, "step_name": "Deburring & Finishing", "duration_hours": 1}
                        ]
                    },
                    {
                        "operation_code": "QUALITY-TEST",
                        "operation_name": "Final Quality Testing",
                        "operation_type": "manufacturing",
                        "description": "Comprehensive quality testing before shipment",
                        "steps": [
                            {"step_number": 1, "step_name": "Visual Inspection", "duration_hours": 0.5, "is_quality_control": True},
                            {"step_number": 2, "step_name": "Functional Testing", "duration_hours": 1, "is_quality_control": True},
                            {"step_number": 3, "step_name": "Certification", "duration_hours": 0.25}
                        ]
                    }
                ],
                "product_categories": ["Raw Materials", "Components", "Work-In-Progress", "Finished Goods", "Packaging Materials"],
                "recommended_accounts": [
                    {"account_code": "1410", "account_name": "Raw Materials Inventory", "account_type": "asset"},
                    {"account_code": "1420", "account_name": "Work-In-Progress (WIP)", "account_type": "asset"},
                    {"account_code": "1430", "account_name": "Finished Goods Inventory", "account_type": "asset"},
                    {"account_code": "5120", "account_name": "Manufacturing Overhead", "account_type": "expense"},
                    {"account_code": "5130", "account_name": "Quality Control Costs", "account_type": "expense"}
                ]
            }
        },
        {
            "template_code": "RETAIL",
            "template_name": "Retail & E-commerce",
            "industry_type": "retail",
            "description": "Template for retail businesses with store operations, inventory management, and sales",
            "template_config": {
                "operations": [
                    {
                        "operation_code": "RECEIVING",
                        "operation_name": "Goods Receiving",
                        "operation_type": "retail",
                        "description": "Receiving and processing incoming inventory",
                        "steps": [
                            {"step_number": 1, "step_name": "Delivery Verification", "duration_hours": 0.5},
                            {"step_number": 2, "step_name": "Quality Check", "duration_hours": 1, "is_quality_control": True},
                            {"step_number": 3, "step_name": "Shelving/Storage", "duration_hours": 2}
                        ]
                    },
                    {
                        "operation_code": "REPLENISHMENT",
                        "operation_name": "Shelf Replenishment",
                        "operation_type": "retail",
                        "description": "Restocking store shelves from backroom",
                        "steps": [
                            {"step_number": 1, "step_name": "Inventory Count", "duration_hours": 1},
                            {"step_number": 2, "step_name": "Product Retrieval", "duration_hours": 0.5},
                            {"step_number": 3, "step_name": "Shelf Stocking", "duration_hours": 1.5}
                        ]
                    },
                    {
                        "operation_code": "ECOMMERCE-PICK",
                        "operation_name": "E-commerce Order Picking",
                        "operation_type": "retail",
                        "description": "Pick and pack online orders for shipping",
                        "steps": [
                            {"step_number": 1, "step_name": "Order Picking", "duration_hours": 0.5},
                            {"step_number": 2, "step_name": "Packing", "duration_hours": 0.25},
                            {"step_number": 3, "step_name": "Shipping Label", "duration_hours": 0.1}
                        ]
                    }
                ],
                "product_categories": ["Merchandise", "Promotional Items", "Packaging Supplies", "Store Supplies"],
                "recommended_accounts": [
                    {"account_code": "1440", "account_name": "Retail Merchandise Inventory", "account_type": "asset"},
                    {"account_code": "4010", "account_name": "Retail Sales Revenue", "account_type": "revenue"},
                    {"account_code": "5010", "account_name": "Cost of Goods Sold - Retail", "account_type": "expense"},
                    {"account_code": "5140", "account_name": "Store Operating Expenses", "account_type": "expense"}
                ]
            }
        }
    ]
    
    created_count = 0
    for template_data in templates:
        # Check if template already exists
        existing = db.query(models.IndustryTemplate).filter(
            models.IndustryTemplate.template_code == template_data["template_code"]
        ).first()
        
        if not existing:
            new_template = models.IndustryTemplate(**template_data)
            db.add(new_template)
            created_count += 1
    
    db.commit()
    return {"message": f"Seeded {created_count} industry templates", "total_templates": len(templates)}

@app.get("/api/industry-templates")
def get_industry_templates(db: Session = Depends(get_db)):
    """Get all available industry templates"""
    templates = db.query(models.IndustryTemplate).filter(
        models.IndustryTemplate.is_active == True
    ).all()
    return templates

@app.post("/api/industry-templates/{template_id}/apply")
def apply_industry_template(
    template_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Apply an industry template to the current company"""
    # Get template
    template = db.query(models.IndustryTemplate).filter(
        models.IndustryTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if already applied
    existing = db.query(models.CompanyIndustryTemplate).filter(
        models.CompanyIndustryTemplate.company_id == current_user.company_id,
        models.CompanyIndustryTemplate.template_id == template_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template already applied to this company")
    
    # Apply template operations
    config = template.template_config
    operations_created = 0
    
    if 'operations' in config:
        for op_data in config['operations']:
            # Extract steps before creating operation (avoid passing nested dict to model)
            steps_data = op_data.pop('steps', [])
            
            new_operation = models.Operation(
                company_id=current_user.company_id,
                created_by=current_user.id,
                **op_data
            )
            db.add(new_operation)
            db.flush()
            
            # Add steps
            for step_data in steps_data:
                step = models.OperationStep(
                    operation_id=new_operation.id,
                    **step_data
                )
                db.add(step)
            
            operations_created += 1
    
    # Record template application
    application = models.CompanyIndustryTemplate(
        company_id=current_user.company_id,
        template_id=template_id,
        applied_by=current_user.id
    )
    db.add(application)
    
    db.commit()
    
    return {
        "message": f"Applied {template.template_name} template",
        "operations_created": operations_created,
        "product_categories": config.get('product_categories', []),
        "recommended_accounts": config.get('recommended_accounts', [])
    }

# OCR & Document Intelligence Endpoints
from ocr_service import OCRService
from fastapi import File, UploadFile
import shutil
import mimetypes

ocr_service = OCRService()

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "invoice",
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a document (invoice, receipt, etc.) for OCR processing"""
    
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}")
    
    upload_dir = "uploads/documents"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    file_id = str(uuid.uuid4())
    file_path = f"{upload_dir}/{file_id}.{file_ext}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_size = os.path.getsize(file_path)
    
    document = models.DocumentUpload(
        company_id=current_user.company_id,
        document_type=document_type,
        file_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type,
        uploaded_by=current_user.id
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return document

@app.post("/api/documents/{document_id}/process")
def process_document_ocr(
    document_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Process document with Claude AI Vision OCR"""
    
    document = db.query(models.DocumentUpload).filter(
        models.DocumentUpload.id == document_id,
        models.DocumentUpload.company_id == current_user.company_id
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.ocr_status == "processing":
        raise HTTPException(status_code=400, detail="Document is already being processed")
    
    document.ocr_status = "processing"
    db.commit()
    
    try:
        result = ocr_service.process_document(document.file_path, document.document_type)
        
        ocr_result = models.OCRResult(
            document_id=document.id,
            company_id=current_user.company_id,
            extracted_text=result['extracted_text'],
            structured_data=result['structured_data'],
            confidence_score=result['confidence_score'],
            ai_model=result['ai_model'],
            processing_time_ms=result['processing_time_ms']
        )
        db.add(ocr_result)
        
        if document.document_type == "invoice":
            invoice_data = result['structured_data']
            if 'supplier' in invoice_data and 'invoice_details' in invoice_data:
                suppliers = db.query(models.Supplier).filter(
                    models.Supplier.company_id == current_user.company_id
                ).all()
                
                match_result = ocr_service.match_supplier(invoice_data, suppliers)
                
                extracted_invoice = models.ExtractedInvoiceData(
                    ocr_result_id=ocr_result.id,
                    company_id=current_user.company_id,
                    supplier_name=invoice_data['supplier'].get('name'),
                    supplier_tax_id=invoice_data['supplier'].get('tax_id'),
                    supplier_address=invoice_data['supplier'].get('address'),
                    supplier_phone=invoice_data['supplier'].get('phone'),
                    supplier_email=invoice_data['supplier'].get('email'),
                    invoice_number=invoice_data['invoice_details'].get('invoice_number'),
                    invoice_date=invoice_data['invoice_details'].get('invoice_date'),
                    due_date=invoice_data['invoice_details'].get('due_date'),
                    purchase_order_number=invoice_data['invoice_details'].get('purchase_order_number'),
                    currency=invoice_data['financial'].get('currency', 'ZMW'),
                    subtotal=invoice_data['financial'].get('subtotal', 0.0),
                    tax_amount=invoice_data['financial'].get('tax_amount', 0.0),
                    total_amount=invoice_data['financial'].get('total_amount'),
                    amount_paid=invoice_data['financial'].get('amount_paid', 0.0),
                    amount_due=invoice_data['financial'].get('amount_due'),
                    line_items=invoice_data.get('line_items', []),
                    matched_supplier_id=match_result['supplier_id'] if match_result else None,
                    match_confidence=match_result['confidence'] if match_result else None
                )
                db.add(extracted_invoice)
        
        elif document.document_type == "receipt":
            receipt_data = result['structured_data']
            if 'merchant' in receipt_data and 'receipt_details' in receipt_data:
                expense_category, category_confidence = ocr_service.suggest_expense_category(receipt_data)
                
                extracted_receipt = models.ExtractedReceiptData(
                    ocr_result_id=ocr_result.id,
                    company_id=current_user.company_id,
                    merchant_name=receipt_data['merchant'].get('name'),
                    merchant_address=receipt_data['merchant'].get('address'),
                    merchant_phone=receipt_data['merchant'].get('phone'),
                    merchant_tax_id=receipt_data['merchant'].get('tax_id'),
                    receipt_number=receipt_data['receipt_details'].get('receipt_number'),
                    receipt_date=receipt_data['receipt_details'].get('receipt_date'),
                    receipt_time=receipt_data['receipt_details'].get('receipt_time'),
                    currency=receipt_data['financial'].get('currency', 'ZMW'),
                    subtotal=receipt_data['financial'].get('subtotal', 0.0),
                    tax_amount=receipt_data['financial'].get('tax_amount', 0.0),
                    tip_amount=receipt_data['financial'].get('tip_amount', 0.0),
                    total_amount=receipt_data['financial'].get('total_amount'),
                    payment_method=receipt_data['payment'].get('payment_method') if 'payment' in receipt_data else None,
                    card_last_four=receipt_data['payment'].get('card_last_four') if 'payment' in receipt_data else None,
                    line_items=receipt_data.get('line_items', []),
                    expense_category=expense_category,
                    category_confidence=category_confidence
                )
                db.add(extracted_receipt)
        
        document.ocr_status = "completed"
        document.ocr_processed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(ocr_result)
        
        return ocr_result
        
    except Exception as e:
        document.ocr_status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

@app.get("/api/documents")
def get_documents(
    document_type: str = None,
    ocr_status: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get uploaded documents"""
    query = db.query(models.DocumentUpload).filter(
        models.DocumentUpload.company_id == current_user.company_id
    )
    
    if document_type:
        query = query.filter(models.DocumentUpload.document_type == document_type)
    if ocr_status:
        query = query.filter(models.DocumentUpload.ocr_status == ocr_status)
    
    documents = query.order_by(models.DocumentUpload.uploaded_at.desc()).all()
    return documents

@app.get("/api/ocr-results/{result_id}")
def get_ocr_result(
    result_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get OCR result with extracted data"""
    ocr_result = db.query(models.OCRResult).filter(
        models.OCRResult.id == result_id,
        models.OCRResult.company_id == current_user.company_id
    ).first()
    if not ocr_result:
        raise HTTPException(status_code=404, detail="OCR result not found")
    
    extracted_invoice = db.query(models.ExtractedInvoiceData).filter(
        models.ExtractedInvoiceData.ocr_result_id == result_id
    ).first()
    
    extracted_receipt = db.query(models.ExtractedReceiptData).filter(
        models.ExtractedReceiptData.ocr_result_id == result_id
    ).first()
    
    return {
        "ocr_result": ocr_result,
        "extracted_invoice": extracted_invoice,
        "extracted_receipt": extracted_receipt
    }

@app.post("/api/ocr-results/{result_id}/approve")
def approve_ocr_result(
    result_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Approve OCR extraction result"""
    ocr_result = db.query(models.OCRResult).filter(
        models.OCRResult.id == result_id,
        models.OCRResult.company_id == current_user.company_id
    ).first()
    if not ocr_result:
        raise HTTPException(status_code=404, detail="OCR result not found")
    
    ocr_result.validation_status = "approved"
    ocr_result.validated_by = current_user.id
    ocr_result.validated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "OCR result approved"}

@app.post("/api/ocr-results/{result_id}/reject")
def reject_ocr_result(
    result_id: str,
    reason: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Reject OCR extraction result"""
    ocr_result = db.query(models.OCRResult).filter(
        models.OCRResult.id == result_id,
        models.OCRResult.company_id == current_user.company_id
    ).first()
    if not ocr_result:
        raise HTTPException(status_code=404, detail="OCR result not found")
    
    ocr_result.validation_status = "rejected"
    ocr_result.validated_by = current_user.id
    ocr_result.validated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "OCR result rejected"}

@app.get("/api/extracted-invoices")
def get_extracted_invoices(
    status: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all extracted invoice data"""
    query = db.query(models.ExtractedInvoiceData).filter(
        models.ExtractedInvoiceData.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.ExtractedInvoiceData.status == status)
    
    invoices = query.order_by(models.ExtractedInvoiceData.created_at.desc()).all()
    return invoices

@app.get("/api/extracted-receipts")
def get_extracted_receipts(
    status: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all extracted receipt data"""
    query = db.query(models.ExtractedReceiptData).filter(
        models.ExtractedReceiptData.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.ExtractedReceiptData.status == status)
    
    receipts = query.order_by(models.ExtractedReceiptData.created_at.desc()).all()
    return receipts

# Advanced HR Endpoints

# Employment Contracts
@app.post("/api/employment-contracts")
def create_employment_contract(
    contract: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new employment contract"""
    # Validate employee
    employee = db.query(models.Employee).filter(
        models.Employee.id == contract['employee_id'],
        models.Employee.company_id == current_user.company_id
    ).first()
    if not employee:
        raise HTTPException(status_code=400, detail="Invalid employee")
    
    # Validate department if provided
    if contract.get('department_id'):
        dept = db.query(models.Department).filter(
            models.Department.id == contract['department_id'],
            models.Department.company_id == current_user.company_id
        ).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Invalid department")
    
    # Generate contract number
    count = db.query(models.EmploymentContract).filter(
        models.EmploymentContract.company_id == current_user.company_id
    ).count()
    contract_number = f"EC-{count + 1:05d}"
    
    new_contract = models.EmploymentContract(
        company_id=current_user.company_id,
        contract_number=contract_number,
        created_by=current_user.id,
        **contract
    )
    db.add(new_contract)
    db.commit()
    db.refresh(new_contract)
    return new_contract

@app.get("/api/employment-contracts")
def get_employment_contracts(
    employee_id: str = None,
    status: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get employment contracts"""
    query = db.query(models.EmploymentContract).filter(
        models.EmploymentContract.company_id == current_user.company_id
    )
    
    if employee_id:
        query = query.filter(models.EmploymentContract.employee_id == employee_id)
    if status:
        query = query.filter(models.EmploymentContract.status == status)
    
    contracts = query.order_by(models.EmploymentContract.created_at.desc()).all()
    return contracts

@app.put("/api/employment-contracts/{contract_id}")
def update_employment_contract(
    contract_id: str,
    contract_data: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update an employment contract"""
    contract = db.query(models.EmploymentContract).filter(
        models.EmploymentContract.id == contract_id,
        models.EmploymentContract.company_id == current_user.company_id
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    for key, value in contract_data.items():
        if hasattr(contract, key):
            setattr(contract, key, value)
    
    db.commit()
    db.refresh(contract)
    return contract

@app.post("/api/employment-contracts/{contract_id}/activate")
def activate_employment_contract(
    contract_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Activate an employment contract"""
    contract = db.query(models.EmploymentContract).filter(
        models.EmploymentContract.id == contract_id,
        models.EmploymentContract.company_id == current_user.company_id
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    contract.status = "active"
    contract.signed_by_employer_at = datetime.utcnow()
    contract.signed_by_employer_id = current_user.id
    db.commit()
    return {"message": "Contract activated"}

# Employee Skills
@app.post("/api/employee-skills")
def create_employee_skill(
    skill: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Add a skill to an employee"""
    # Validate employee
    employee = db.query(models.Employee).filter(
        models.Employee.id == skill['employee_id'],
        models.Employee.company_id == current_user.company_id
    ).first()
    if not employee:
        raise HTTPException(status_code=400, detail="Invalid employee")
    
    new_skill = models.EmployeeSkill(
        company_id=current_user.company_id,
        **skill
    )
    db.add(new_skill)
    db.commit()
    db.refresh(new_skill)
    return new_skill

@app.get("/api/employee-skills")
def get_employee_skills(
    employee_id: str = None,
    skill_category: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get employee skills"""
    query = db.query(models.EmployeeSkill).filter(
        models.EmployeeSkill.company_id == current_user.company_id
    )
    
    if employee_id:
        query = query.filter(models.EmployeeSkill.employee_id == employee_id)
    if skill_category:
        query = query.filter(models.EmployeeSkill.skill_category == skill_category)
    
    skills = query.order_by(models.EmployeeSkill.created_at.desc()).all()
    return skills

@app.put("/api/employee-skills/{skill_id}")
def update_employee_skill(
    skill_id: str,
    skill_data: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update an employee skill"""
    skill = db.query(models.EmployeeSkill).filter(
        models.EmployeeSkill.id == skill_id,
        models.EmployeeSkill.company_id == current_user.company_id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    for key, value in skill_data.items():
        if hasattr(skill, key):
            setattr(skill, key, value)
    
    db.commit()
    db.refresh(skill)
    return skill

@app.delete("/api/employee-skills/{skill_id}")
def delete_employee_skill(
    skill_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an employee skill"""
    skill = db.query(models.EmployeeSkill).filter(
        models.EmployeeSkill.id == skill_id,
        models.EmployeeSkill.company_id == current_user.company_id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    db.delete(skill)
    db.commit()
    return {"message": "Skill deleted"}

# Job Requisitions
@app.post("/api/job-requisitions")
def create_job_requisition(
    requisition: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new job requisition"""
    # Validate department
    dept = db.query(models.Department).filter(
        models.Department.id == requisition['department_id'],
        models.Department.company_id == current_user.company_id
    ).first()
    if not dept:
        raise HTTPException(status_code=400, detail="Invalid department")
    
    # Generate requisition number
    count = db.query(models.JobRequisition).filter(
        models.JobRequisition.company_id == current_user.company_id
    ).count()
    requisition_number = f"JR-{count + 1:05d}"
    
    new_requisition = models.JobRequisition(
        company_id=current_user.company_id,
        requisition_number=requisition_number,
        requested_by=current_user.id,
        created_by=current_user.id,
        **requisition
    )
    db.add(new_requisition)
    db.commit()
    db.refresh(new_requisition)
    return new_requisition

@app.get("/api/job-requisitions")
def get_job_requisitions(
    department_id: str = None,
    status: str = None,
    approval_status: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get job requisitions"""
    query = db.query(models.JobRequisition).filter(
        models.JobRequisition.company_id == current_user.company_id
    )
    
    if department_id:
        query = query.filter(models.JobRequisition.department_id == department_id)
    if status:
        query = query.filter(models.JobRequisition.status == status)
    if approval_status:
        query = query.filter(models.JobRequisition.approval_status == approval_status)
    
    requisitions = query.order_by(models.JobRequisition.created_at.desc()).all()
    return requisitions

@app.post("/api/job-requisitions/{requisition_id}/approve")
def approve_job_requisition(
    requisition_id: str,
    approval_notes: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Approve a job requisition"""
    requisition = db.query(models.JobRequisition).filter(
        models.JobRequisition.id == requisition_id,
        models.JobRequisition.company_id == current_user.company_id
    ).first()
    if not requisition:
        raise HTTPException(status_code=404, detail="Requisition not found")
    
    requisition.approval_status = "approved"
    requisition.approved_by = current_user.id
    requisition.approved_at = datetime.utcnow()
    requisition.approval_notes = approval_notes
    requisition.status = "open"
    
    db.commit()
    return {"message": "Requisition approved"}

@app.post("/api/job-requisitions/{requisition_id}/fill")
def fill_job_requisition(
    requisition_id: str,
    employee_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a job requisition as filled"""
    requisition = db.query(models.JobRequisition).filter(
        models.JobRequisition.id == requisition_id,
        models.JobRequisition.company_id == current_user.company_id
    ).first()
    if not requisition:
        raise HTTPException(status_code=404, detail="Requisition not found")
    
    # Validate employee
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id,
        models.Employee.company_id == current_user.company_id
    ).first()
    if not employee:
        raise HTTPException(status_code=400, detail="Invalid employee")
    
    requisition.status = "filled"
    requisition.filled_by_employee_id = employee_id
    requisition.filled_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Requisition marked as filled"}

# Performance Reviews
@app.post("/api/performance-reviews")
def create_performance_review(
    review: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new performance review"""
    # Validate employee
    employee = db.query(models.Employee).filter(
        models.Employee.id == review['employee_id'],
        models.Employee.company_id == current_user.company_id
    ).first()
    if not employee:
        raise HTTPException(status_code=400, detail="Invalid employee")
    
    new_review = models.PerformanceReview(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **review
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

@app.get("/api/performance-reviews")
def get_performance_reviews(
    employee_id: str = None,
    review_type: str = None,
    status: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance reviews"""
    query = db.query(models.PerformanceReview).filter(
        models.PerformanceReview.company_id == current_user.company_id
    )
    
    if employee_id:
        query = query.filter(models.PerformanceReview.employee_id == employee_id)
    if review_type:
        query = query.filter(models.PerformanceReview.review_type == review_type)
    if status:
        query = query.filter(models.PerformanceReview.status == status)
    
    reviews = query.order_by(models.PerformanceReview.created_at.desc()).all()
    return reviews

@app.put("/api/performance-reviews/{review_id}")
def update_performance_review(
    review_id: str,
    review_data: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update a performance review"""
    review = db.query(models.PerformanceReview).filter(
        models.PerformanceReview.id == review_id,
        models.PerformanceReview.company_id == current_user.company_id
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    for key, value in review_data.items():
        if hasattr(review, key):
            setattr(review, key, value)
    
    db.commit()
    db.refresh(review)
    return review

@app.post("/api/performance-reviews/{review_id}/complete")
def complete_performance_review(
    review_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Complete a performance review"""
    review = db.query(models.PerformanceReview).filter(
        models.PerformanceReview.id == review_id,
        models.PerformanceReview.company_id == current_user.company_id
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.status = "completed"
    review.reviewed_by = current_user.id
    review.reviewed_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Performance review completed"}

@app.post("/api/performance-reviews/{review_id}/acknowledge")
def acknowledge_performance_review(
    review_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Employee acknowledges performance review"""
    review = db.query(models.PerformanceReview).filter(
        models.PerformanceReview.id == review_id,
        models.PerformanceReview.company_id == current_user.company_id
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.status = "acknowledged"
    review.acknowledged_by_employee_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Performance review acknowledged"}

# Banking API Integration Endpoints
from banking_service import BankingService

banking_service = BankingService()

@app.post("/api/bank-connections")
def create_bank_connection(
    connection: dict,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new bank connection"""
    # Validate bank code
    supported_banks = ['zanaco', 'absa', 'fnb', 'stanbic']
    if connection['bank_code'] not in supported_banks:
        raise HTTPException(status_code=400, detail=f"Unsupported bank. Supported: {', '.join(supported_banks)}")
    
    # Test connection before saving
    credentials = {
        "username": connection.get('api_username'),
        "api_key": connection.get('api_key_encrypted'),
        "endpoint": connection.get('api_endpoint')
    }
    
    test_result = banking_service.test_connection(connection['bank_code'], credentials)
    if not test_result['success']:
        raise HTTPException(status_code=400, detail=f"Connection test failed: {test_result.get('error')}")
    
    new_connection = models.BankConnection(
        company_id=current_user.company_id,
        created_by=current_user.id,
        connection_status="connected",
        **connection
    )
    db.add(new_connection)
    db.commit()
    db.refresh(new_connection)
    return new_connection

@app.get("/api/bank-connections")
def get_bank_connections(
    is_active: bool = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bank connections"""
    query = db.query(models.BankConnection).filter(
        models.BankConnection.company_id == current_user.company_id
    )
    
    if is_active is not None:
        query = query.filter(models.BankConnection.is_active == is_active)
    
    connections = query.order_by(models.BankConnection.created_at.desc()).all()
    return connections

@app.get("/api/bank-connections/{connection_id}")
def get_bank_connection(
    connection_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific bank connection"""
    connection = db.query(models.BankConnection).filter(
        models.BankConnection.id == connection_id,
        models.BankConnection.company_id == current_user.company_id
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    return connection

@app.post("/api/bank-connections/{connection_id}/sync")
def sync_bank_transactions(
    connection_id: str,
    days_back: int = 7,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Sync transactions from bank API"""
    connection = db.query(models.BankConnection).filter(
        models.BankConnection.id == connection_id,
        models.BankConnection.company_id == current_user.company_id
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    
    # Create sync history record
    from_date = datetime.now() - timedelta(days=days_back)
    to_date = datetime.now()
    
    sync_history = models.BankSyncHistory(
        company_id=current_user.company_id,
        bank_connection_id=connection_id,
        sync_type="manual",
        from_date=from_date.date(),
        to_date=to_date.date(),
        triggered_by=current_user.id
    )
    db.add(sync_history)
    db.flush()
    
    try:
        # Fetch transactions from bank
        credentials = {
            "username": connection.api_username,
            "api_key": connection.api_key_encrypted,
            "endpoint": connection.api_endpoint
        }
        
        result = banking_service.fetch_transactions(
            connection.bank_code,
            credentials,
            connection.account_number,
            from_date,
            to_date
        )
        
        if not result['success']:
            sync_history.status = "failed"
            sync_history.error_message = result.get('error')
            sync_history.sync_completed_at = datetime.utcnow()
            db.commit()
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        transactions = result['transactions']
        
        # Save transactions
        new_count = 0
        updated_count = 0
        failed_count = 0
        
        for trans_data in transactions:
            try:
                # Check if transaction already exists (composite unique: connection + transaction ID)
                existing = db.query(models.BankTransaction).filter(
                    models.BankTransaction.bank_connection_id == connection_id,
                    models.BankTransaction.bank_transaction_id == trans_data['bank_transaction_id']
                ).first()
                
                if existing:
                    # Update existing transaction
                    for key, value in trans_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    updated_count += 1
                else:
                    # Create new transaction
                    new_trans = models.BankTransaction(
                        company_id=current_user.company_id,
                        bank_connection_id=connection_id,
                        import_batch_id=sync_history.id,
                        **trans_data
                    )
                    db.add(new_trans)
                    new_count += 1
            except Exception as e:
                failed_count += 1
                continue
        
        # Update sync history
        sync_history.status = "completed" if failed_count == 0 else "partial"
        sync_history.transactions_fetched = len(transactions)
        sync_history.transactions_new = new_count
        sync_history.transactions_updated = updated_count
        sync_history.transactions_failed = failed_count
        sync_history.sync_completed_at = datetime.utcnow()
        
        # Update connection
        connection.last_sync_at = datetime.utcnow()
        connection.last_sync_status = sync_history.status
        
        db.commit()
        
        return {
            "message": "Sync completed",
            "sync_id": sync_history.id,
            "transactions_fetched": len(transactions),
            "transactions_new": new_count,
            "transactions_updated": updated_count,
            "transactions_failed": failed_count,
            "status": sync_history.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        sync_history.status = "failed"
        sync_history.error_message = str(e)
        sync_history.sync_completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@app.get("/api/bank-transactions")
def get_bank_transactions(
    connection_id: str = None,
    is_reconciled: bool = None,
    from_date: str = None,
    to_date: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get bank transactions"""
    query = db.query(models.BankTransaction).filter(
        models.BankTransaction.company_id == current_user.company_id
    )
    
    if connection_id:
        query = query.filter(models.BankTransaction.bank_connection_id == connection_id)
    if is_reconciled is not None:
        query = query.filter(models.BankTransaction.is_reconciled == is_reconciled)
    if from_date:
        query = query.filter(models.BankTransaction.transaction_date >= datetime.fromisoformat(from_date).date())
    if to_date:
        query = query.filter(models.BankTransaction.transaction_date <= datetime.fromisoformat(to_date).date())
    
    transactions = query.order_by(models.BankTransaction.transaction_date.desc()).limit(500).all()
    return transactions

@app.get("/api/bank-connections/{connection_id}/balance")
def get_bank_balance(
    connection_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get current bank account balance"""
    connection = db.query(models.BankConnection).filter(
        models.BankConnection.id == connection_id,
        models.BankConnection.company_id == current_user.company_id
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    
    credentials = {
        "username": connection.api_username,
        "api_key": connection.api_key_encrypted,
        "endpoint": connection.api_endpoint
    }
    
    result = banking_service.get_account_balance(
        connection.bank_code,
        credentials,
        connection.account_number
    )
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error'))
    
    return result['balance']

@app.get("/api/bank-sync-history")
def get_sync_history(
    connection_id: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get bank sync history"""
    query = db.query(models.BankSyncHistory).filter(
        models.BankSyncHistory.company_id == current_user.company_id
    )
    
    if connection_id:
        query = query.filter(models.BankSyncHistory.bank_connection_id == connection_id)
    
    history = query.order_by(models.BankSyncHistory.sync_started_at.desc()).limit(100).all()
    return history

@app.get("/api/supported-banks")
def get_supported_banks():
    """Get list of supported banks"""
    return {
        "banks": [
            {"code": "zanaco", "name": "ZANACO", "full_name": "Zambia National Commercial Bank"},
            {"code": "absa", "name": "ABSA", "full_name": "ABSA Bank Zambia"},
            {"code": "fnb", "name": "FNB", "full_name": "First National Bank Zambia"},
            {"code": "stanbic", "name": "Stanbic", "full_name": "Stanbic Bank Zambia"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

# ============================================================================
# SETTINGS MODULE ENDPOINTS
# ============================================================================

# System Settings Endpoints
@app.get("/api/settings/system", response_model=List[schemas.SystemSettingResponse])
def get_system_settings(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all system settings for the company"""
    query = db.query(models.SystemSetting).filter(
        models.SystemSetting.company_id == current_user.company_id
    )
    
    if category:
        query = query.filter(models.SystemSetting.category == category)
    
    return query.all()

@app.post("/api/settings/system", response_model=schemas.SystemSettingResponse)
def create_system_setting(
    setting: schemas.SystemSettingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Create a new system setting"""
    db_setting = models.SystemSetting(
        company_id=current_user.company_id,
        updated_by=current_user.id,
        **setting.dict()
    )
    db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting

@app.put("/api/settings/system/{setting_id}", response_model=schemas.SystemSettingResponse)
def update_system_setting(
    setting_id: str,
    setting_update: schemas.SystemSettingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Update a system setting"""
    db_setting = db.query(models.SystemSetting).filter(
        models.SystemSetting.id == setting_id,
        models.SystemSetting.company_id == current_user.company_id
    ).first()
    
    if not db_setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    for key, value in setting_update.dict(exclude_unset=True).items():
        setattr(db_setting, key, value)
    
    db_setting.updated_by = current_user.id
    db.commit()
    db.refresh(db_setting)
    return db_setting

@app.delete("/api/settings/system/{setting_id}")
def delete_system_setting(
    setting_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Delete a system setting"""
    db_setting = db.query(models.SystemSetting).filter(
        models.SystemSetting.id == setting_id,
        models.SystemSetting.company_id == current_user.company_id
    ).first()
    
    if not db_setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    db.delete(db_setting)
    db.commit()
    return {"message": "Setting deleted successfully"}

# Tax Settings Endpoints
@app.get("/api/settings/tax", response_model=List[schemas.TaxSettingResponse])
def get_tax_settings(
    tax_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all tax settings for the company"""
    query = db.query(models.TaxSetting).filter(
        models.TaxSetting.company_id == current_user.company_id
    )
    
    if tax_type:
        query = query.filter(models.TaxSetting.tax_type == tax_type)
    if is_active is not None:
        query = query.filter(models.TaxSetting.is_active == is_active)
    
    return query.all()

@app.post("/api/settings/tax", response_model=schemas.TaxSettingResponse)
def create_tax_setting(
    tax_setting: schemas.TaxSettingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Create a new tax setting"""
    db_tax = models.TaxSetting(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **tax_setting.dict()
    )
    db.add(db_tax)
    db.commit()
    db.refresh(db_tax)
    return db_tax

@app.put("/api/settings/tax/{tax_id}", response_model=schemas.TaxSettingResponse)
def update_tax_setting(
    tax_id: str,
    tax_update: schemas.TaxSettingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Update a tax setting"""
    db_tax = db.query(models.TaxSetting).filter(
        models.TaxSetting.id == tax_id,
        models.TaxSetting.company_id == current_user.company_id
    ).first()
    
    if not db_tax:
        raise HTTPException(status_code=404, detail="Tax setting not found")
    
    for key, value in tax_update.dict(exclude_unset=True).items():
        setattr(db_tax, key, value)
    
    db.commit()
    db.refresh(db_tax)
    return db_tax

@app.delete("/api/settings/tax/{tax_id}")
def delete_tax_setting(
    tax_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Delete a tax setting"""
    db_tax = db.query(models.TaxSetting).filter(
        models.TaxSetting.id == tax_id,
        models.TaxSetting.company_id == current_user.company_id
    ).first()
    
    if not db_tax:
        raise HTTPException(status_code=404, detail="Tax setting not found")
    
    db.delete(db_tax)
    db.commit()
    return {"message": "Tax setting deleted successfully"}

# Email Templates Endpoints
@app.get("/api/settings/email-templates", response_model=List[schemas.EmailTemplateResponse])
def get_email_templates(
    template_code: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all email templates"""
    query = db.query(models.EmailTemplate).filter(
        models.EmailTemplate.company_id == current_user.company_id
    )
    
    if template_code:
        query = query.filter(models.EmailTemplate.template_code == template_code)
    if is_active is not None:
        query = query.filter(models.EmailTemplate.is_active == is_active)
    
    return query.all()

@app.post("/api/settings/email-templates", response_model=schemas.EmailTemplateResponse)
def create_email_template(
    template: schemas.EmailTemplateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Create a new email template"""
    db_template = models.EmailTemplate(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **template.dict()
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@app.put("/api/settings/email-templates/{template_id}", response_model=schemas.EmailTemplateResponse)
def update_email_template(
    template_id: str,
    template_update: schemas.EmailTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Update an email template"""
    db_template = db.query(models.EmailTemplate).filter(
        models.EmailTemplate.id == template_id,
        models.EmailTemplate.company_id == current_user.company_id
    ).first()
    
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if db_template.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system templates")
    
    for key, value in template_update.dict(exclude_unset=True).items():
        setattr(db_template, key, value)
    
    db.commit()
    db.refresh(db_template)
    return db_template

@app.delete("/api/settings/email-templates/{template_id}")
def delete_email_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Delete an email template"""
    db_template = db.query(models.EmailTemplate).filter(
        models.EmailTemplate.id == template_id,
        models.EmailTemplate.company_id == current_user.company_id
    ).first()
    
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if db_template.is_system:
        raise HTTPException(status_code=403, detail="Cannot delete system templates")
    
    db.delete(db_template)
    db.commit()
    return {"message": "Template deleted successfully"}

# Salary Components Endpoints
@app.get("/api/settings/salary-components", response_model=List[schemas.SalaryComponentResponse])
def get_salary_components(
    component_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all salary components"""
    query = db.query(models.SalaryComponent).filter(
        models.SalaryComponent.company_id == current_user.company_id
    ).order_by(models.SalaryComponent.display_order)
    
    if component_type:
        query = query.filter(models.SalaryComponent.component_type == component_type)
    if is_active is not None:
        query = query.filter(models.SalaryComponent.is_active == is_active)
    
    return query.all()

@app.post("/api/settings/salary-components", response_model=schemas.SalaryComponentResponse)
def create_salary_component(
    component: schemas.SalaryComponentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Create a new salary component"""
    db_component = models.SalaryComponent(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **component.dict()
    )
    db.add(db_component)
    db.commit()
    db.refresh(db_component)
    return db_component

@app.put("/api/settings/salary-components/{component_id}", response_model=schemas.SalaryComponentResponse)
def update_salary_component(
    component_id: str,
    component_update: schemas.SalaryComponentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Update a salary component"""
    db_component = db.query(models.SalaryComponent).filter(
        models.SalaryComponent.id == component_id,
        models.SalaryComponent.company_id == current_user.company_id
    ).first()
    
    if not db_component:
        raise HTTPException(status_code=404, detail="Salary component not found")
    
    for key, value in component_update.dict(exclude_unset=True).items():
        setattr(db_component, key, value)
    
    db.commit()
    db.refresh(db_component)
    return db_component

@app.delete("/api/settings/salary-components/{component_id}")
def delete_salary_component(
    component_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Delete a salary component"""
    db_component = db.query(models.SalaryComponent).filter(
        models.SalaryComponent.id == component_id,
        models.SalaryComponent.company_id == current_user.company_id
    ).first()
    
    if not db_component:
        raise HTTPException(status_code=404, detail="Salary component not found")
    
    if db_component.is_statutory:
        raise HTTPException(status_code=403, detail="Cannot delete statutory components")
    
    db.delete(db_component)
    db.commit()
    return {"message": "Salary component deleted successfully"}

# Approval Workflow Rules Endpoints
@app.get("/api/settings/approval-workflows", response_model=List[schemas.ApprovalWorkflowRuleResponse])
def get_approval_workflows(
    entity_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all approval workflow rules"""
    query = db.query(models.ApprovalWorkflowRule).filter(
        models.ApprovalWorkflowRule.company_id == current_user.company_id
    ).order_by(models.ApprovalWorkflowRule.priority)
    
    if entity_type:
        query = query.filter(models.ApprovalWorkflowRule.entity_type == entity_type)
    if is_active is not None:
        query = query.filter(models.ApprovalWorkflowRule.is_active == is_active)
    
    return query.all()

@app.post("/api/settings/approval-workflows", response_model=schemas.ApprovalWorkflowRuleResponse)
def create_approval_workflow(
    workflow: schemas.ApprovalWorkflowRuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Create a new approval workflow rule"""
    db_workflow = models.ApprovalWorkflowRule(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **workflow.dict()
    )
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    return db_workflow

@app.put("/api/settings/approval-workflows/{workflow_id}", response_model=schemas.ApprovalWorkflowRuleResponse)
def update_approval_workflow(
    workflow_id: str,
    workflow_update: schemas.ApprovalWorkflowRuleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Update an approval workflow rule"""
    db_workflow = db.query(models.ApprovalWorkflowRule).filter(
        models.ApprovalWorkflowRule.id == workflow_id,
        models.ApprovalWorkflowRule.company_id == current_user.company_id
    ).first()
    
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    for key, value in workflow_update.dict(exclude_unset=True).items():
        setattr(db_workflow, key, value)
    
    db.commit()
    db.refresh(db_workflow)
    return db_workflow

@app.delete("/api/settings/approval-workflows/{workflow_id}")
def delete_approval_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Delete an approval workflow rule"""
    db_workflow = db.query(models.ApprovalWorkflowRule).filter(
        models.ApprovalWorkflowRule.id == workflow_id,
        models.ApprovalWorkflowRule.company_id == current_user.company_id
    ).first()
    
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    db.delete(db_workflow)
    db.commit()
    return {"message": "Workflow deleted successfully"}

# Leave Type Configuration Endpoints
@app.get("/api/settings/leave-configurations", response_model=List[schemas.LeaveTypeConfigurationResponse])
def get_leave_configurations(
    leave_type_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all leave type configurations"""
    query = db.query(models.LeaveTypeConfiguration).filter(
        models.LeaveTypeConfiguration.company_id == current_user.company_id
    )
    
    if leave_type_id:
        query = query.filter(models.LeaveTypeConfiguration.leave_type_id == leave_type_id)
    
    return query.all()

@app.post("/api/settings/leave-configurations", response_model=schemas.LeaveTypeConfigurationResponse)
def create_leave_configuration(
    config: schemas.LeaveTypeConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Create a new leave type configuration"""
    # Verify leave type exists and belongs to company
    leave_type = db.query(models.LeaveType).filter(
        models.LeaveType.id == config.leave_type_id,
        models.LeaveType.company_id == current_user.company_id
    ).first()
    
    if not leave_type:
        raise HTTPException(status_code=404, detail="Leave type not found")
    
    db_config = models.LeaveTypeConfiguration(
        company_id=current_user.company_id,
        **config.dict()
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@app.put("/api/settings/leave-configurations/{config_id}", response_model=schemas.LeaveTypeConfigurationResponse)
def update_leave_configuration(
    config_id: str,
    config_update: schemas.LeaveTypeConfigurationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Update a leave type configuration"""
    db_config = db.query(models.LeaveTypeConfiguration).filter(
        models.LeaveTypeConfiguration.id == config_id,
        models.LeaveTypeConfiguration.company_id == current_user.company_id
    ).first()
    
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    for key, value in config_update.dict(exclude_unset=True).items():
        setattr(db_config, key, value)
    
    db.commit()
    db.refresh(db_config)
    return db_config

@app.delete("/api/settings/leave-configurations/{config_id}")
def delete_leave_configuration(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Delete a leave type configuration"""
    db_config = db.query(models.LeaveTypeConfiguration).filter(
        models.LeaveTypeConfiguration.id == config_id,
        models.LeaveTypeConfiguration.company_id == current_user.company_id
    ).first()
    
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    db.delete(db_config)
    db.commit()
    return {"message": "Configuration deleted successfully"}

# Seed Default Settings Endpoint
@app.post("/api/settings/seed-defaults")
def seed_default_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Seed default settings for the company (Zambian tax settings, salary components, etc.)"""
    
    # Check if already seeded
    existing = db.query(models.TaxSetting).filter(
        models.TaxSetting.company_id == current_user.company_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Default settings already seeded")
    
    # Create Zambian PAYE Tax Brackets (2024)
    paye_brackets = [
        {"min": 0, "max": 4500, "rate": 0, "fixed": 0},
        {"min": 4501, "max": 6900, "rate": 20, "fixed": 0},
        {"min": 6901, "max": 11100, "rate": 30, "fixed": 480},
        {"min": 11101, "max": 15300, "rate": 35, "fixed": 1740},
        {"min": 15301, "max": 99999999, "rate": 37.5, "fixed": 3210}
    ]
    
    paye_tax = models.TaxSetting(
        company_id=current_user.company_id,
        tax_name="PAYE (Pay As You Earn)",
        tax_type="income_tax",
        jurisdiction="Zambia",
        tax_brackets=paye_brackets,
        is_active=True,
        created_by=current_user.id
    )
    db.add(paye_tax)
    
    # Create NAPSA (National Pension Scheme Authority)
    napsa = models.TaxSetting(
        company_id=current_user.company_id,
        tax_name="NAPSA",
        tax_type="statutory",
        jurisdiction="Zambia",
        employer_rate=5.0,
        employee_rate=5.0,
        applies_to="gross",
        is_active=True,
        created_by=current_user.id
    )
    db.add(napsa)
    
    # Create NHIMA (National Health Insurance Management Authority)
    nhima = models.TaxSetting(
        company_id=current_user.company_id,
        tax_name="NHIMA",
        tax_type="statutory",
        jurisdiction="Zambia",
        employer_rate=1.0,
        employee_rate=1.0,
        applies_to="basic",
        is_active=True,
        created_by=current_user.id
    )
    db.add(nhima)
    
    # Create Standard Salary Components
    components = [
        {"code": "BASIC", "name": "Basic Salary", "type": "earning", "taxable": True, "in_gross": True, "statutory": False, "order": 1},
        {"code": "HRA", "name": "Housing Allowance", "type": "earning", "taxable": True, "in_gross": True, "statutory": False, "order": 2},
        {"code": "TRANS", "name": "Transport Allowance", "type": "earning", "taxable": True, "in_gross": True, "statutory": False, "order": 3},
        {"code": "LUNCH", "name": "Lunch Allowance", "type": "earning", "taxable": True, "in_gross": True, "statutory": False, "order": 4},
        {"code": "PAYE", "name": "PAYE Tax", "type": "deduction", "taxable": False, "in_gross": False, "statutory": True, "stat_type": "paye", "order": 100},
        {"code": "NAPSA_EE", "name": "NAPSA (Employee)", "type": "deduction", "taxable": False, "in_gross": False, "statutory": True, "stat_type": "napsa", "order": 101},
        {"code": "NHIMA_EE", "name": "NHIMA (Employee)", "type": "deduction", "taxable": False, "in_gross": False, "statutory": True, "stat_type": "nhima", "order": 102},
    ]
    
    for comp in components:
        salary_comp = models.SalaryComponent(
            company_id=current_user.company_id,
            component_code=comp["code"],
            component_name=comp["name"],
            component_type=comp["type"],
            is_taxable=comp["taxable"],
            include_in_gross=comp["in_gross"],
            is_statutory=comp["statutory"],
            statutory_type=comp.get("stat_type"),
            display_order=comp["order"],
            created_by=current_user.id
        )
        db.add(salary_comp)
    
    db.commit()
    
    return {
        "message": "Default Zambian tax settings and salary components seeded successfully",
        "tax_settings": 3,
        "salary_components": len(components)
    }

@app.get("/api/notifications", response_model=List[schemas.NotificationResponse])
def get_notifications(
    unread_only: bool = False,
    notification_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Notification).filter(
        models.Notification.company_id == current_user.company_id,
        models.Notification.user_id == current_user.id
    )
    
    if unread_only:
        query = query.filter(models.Notification.is_read == False)
    
    if notification_type:
        query = query.filter(models.Notification.notification_type == notification_type)
    
    notifications = query.order_by(models.Notification.created_at.desc()).offset(offset).limit(limit).all()
    return notifications

@app.get("/api/notifications/unread-count")
def get_unread_count(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    count = db.query(models.Notification).filter(
        models.Notification.company_id == current_user.company_id,
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()
    
    return {"unread_count": count}

@app.post("/api/notifications", response_model=schemas.NotificationResponse)
def create_notification(
    notification: schemas.NotificationCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    target_user = db.query(models.User).filter(
        models.User.id == notification.user_id,
        models.User.company_id == current_user.company_id
    ).first()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found or not in your company")
    
    db_notification = models.Notification(
        company_id=current_user.company_id,
        created_by=current_user.id,
        **notification.model_dump()
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    
    notification_service.send_notification(
        notification=db_notification,
        user_email=target_user.email,
        user_phone=target_user.phone,
        db=db
    )
    
    return db_notification

@app.put("/api/notifications/{notification_id}/mark-read", response_model=schemas.NotificationResponse)
def mark_notification_read(
    notification_id: str,
    is_read: bool = True,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.company_id == current_user.company_id,
        models.Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = is_read
    notification.read_at = datetime.utcnow() if is_read else None
    
    db.commit()
    db.refresh(notification)
    
    return notification

@app.put("/api/notifications/mark-all-read")
def mark_all_notifications_read(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    updated_count = db.query(models.Notification).filter(
        models.Notification.company_id == current_user.company_id,
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).update({
        "is_read": True,
        "read_at": datetime.utcnow()
    })
    
    db.commit()
    
    return {"message": f"Marked {updated_count} notifications as read"}

@app.delete("/api/notifications/{notification_id}")
def delete_notification(
    notification_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.company_id == current_user.company_id,
        models.Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Notification deleted successfully"}

# ============================================================
# AUDIT LOG ENDPOINTS - Compliance & Security Tracking
# ============================================================

@app.get("/api/audit-logs", response_model=List[schemas.AuditLogResponse])
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get audit logs with filtering.
    
    Supports filtering by:
    - Date range (start_date, end_date)
    - User (user_id)
    - Action type (CREATE, UPDATE, DELETE, etc.)
    - Entity type (Invoice, Employee, etc.)
    - Entity ID
    - Status (success, failure, error)
    
    Ordered by timestamp descending (newest first).
    """
    query = db.query(models.AuditLog).filter(
        models.AuditLog.company_id == current_user.company_id
    )
    
    # Apply filters
    if start_date:
        query = query.filter(models.AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(models.AuditLog.timestamp <= end_date)
    if user_id:
        query = query.filter(models.AuditLog.user_id == user_id)
    if action:
        query = query.filter(models.AuditLog.action == action)
    if entity_type:
        query = query.filter(models.AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(models.AuditLog.entity_id == entity_id)
    if status:
        query = query.filter(models.AuditLog.status == status)
    
    # Order by newest first
    query = query.order_by(models.AuditLog.timestamp.desc())
    
    # Pagination
    logs = query.offset(skip).limit(limit).all()
    
    return logs

@app.get("/api/audit-logs/stats")
def get_audit_log_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get audit log statistics for dashboards and analytics.
    
    Returns:
    - Total logs count
    - Actions breakdown (CREATE, UPDATE, DELETE counts)
    - Top users by activity
    - Top entity types
    - Success/failure rates
    - Hourly activity (last 24h)
    """
    from sqlalchemy import func
    
    # Base query with filters
    base_query = db.query(models.AuditLog).filter(
        models.AuditLog.company_id == current_user.company_id
    )
    
    if start_date:
        base_query = base_query.filter(models.AuditLog.timestamp >= start_date)
    if end_date:
        base_query = base_query.filter(models.AuditLog.timestamp <= end_date)
    
    # Total count
    total_logs = base_query.count()
    
    # Actions breakdown
    actions = db.query(
        models.AuditLog.action,
        func.count(models.AuditLog.id).label('count')
    ).filter(
        models.AuditLog.company_id == current_user.company_id
    ).group_by(models.AuditLog.action).all()
    
    actions_breakdown = {action: count for action, count in actions}
    
    # Top users
    top_users = db.query(
        models.AuditLog.user_email,
        func.count(models.AuditLog.id).label('count')
    ).filter(
        models.AuditLog.company_id == current_user.company_id,
        models.AuditLog.user_email.isnot(None)
    ).group_by(models.AuditLog.user_email).order_by(
        func.count(models.AuditLog.id).desc()
    ).limit(10).all()
    
    top_users_list = [{"user_email": email, "count": count} for email, count in top_users]
    
    # Top entity types
    top_entities = db.query(
        models.AuditLog.entity_type,
        func.count(models.AuditLog.id).label('count')
    ).filter(
        models.AuditLog.company_id == current_user.company_id,
        models.AuditLog.entity_type.isnot(None)
    ).group_by(models.AuditLog.entity_type).order_by(
        func.count(models.AuditLog.id).desc()
    ).limit(10).all()
    
    top_entities_list = [{"entity_type": entity, "count": count} for entity, count in top_entities]
    
    # Status breakdown
    status_counts = db.query(
        models.AuditLog.status,
        func.count(models.AuditLog.id).label('count')
    ).filter(
        models.AuditLog.company_id == current_user.company_id
    ).group_by(models.AuditLog.status).all()
    
    status_breakdown = {status: count for status, count in status_counts}
    
    return {
        "total_logs": total_logs,
        "actions_breakdown": actions_breakdown,
        "top_users": top_users_list,
        "top_entities": top_entities_list,
        "status_breakdown": status_breakdown
    }

@app.post("/api/audit-logs/export")
def export_audit_logs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export audit logs to CSV format.
    
    Returns CSV data as downloadable file.
    """
    from io import StringIO
    import csv
    from fastapi.responses import StreamingResponse
    from audit_logger import audit_logger
    
    # Log the export action
    audit_logger.log_export(
        db=db,
        user=current_user,
        entity_type="AuditLog",
        format="CSV",
        filters={
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "action": action,
            "entity_type": entity_type
        }
    )
    
    # Query logs
    query = db.query(models.AuditLog).filter(
        models.AuditLog.company_id == current_user.company_id
    )
    
    if start_date:
        query = query.filter(models.AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(models.AuditLog.timestamp <= end_date)
    if action:
        query = query.filter(models.AuditLog.action == action)
    if entity_type:
        query = query.filter(models.AuditLog.entity_type == entity_type)
    
    logs = query.order_by(models.AuditLog.timestamp.desc()).all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        'Timestamp', 'User', 'Action', 'Entity Type', 'Entity ID',
        'Status', 'IP Address', 'User Agent', 'Changes'
    ])
    
    # Write rows
    for log in logs:
        writer.writerow([
            log.timestamp.isoformat() if log.timestamp else '',
            log.user_email or '',
            log.action or '',
            log.entity_type or '',
            log.entity_id or '',
            log.status or '',
            log.ip_address or '',
            log.user_agent or '',
            str(log.changes) if log.changes else ''
        ])
    
    # Return as downloadable CSV
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )

# Serve static files from frontend build (for production deployment)
frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_build_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_build_path, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Serve API routes normally (they're already defined above)
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404)
        
        # Try to serve the requested file
        file_path = os.path.join(frontend_build_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Otherwise serve index.html for React Router
        return FileResponse(os.path.join(frontend_build_path, "index.html"))

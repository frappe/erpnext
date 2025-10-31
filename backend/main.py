from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
import models
import schemas
import auth
import utils
from database import engine, get_db

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

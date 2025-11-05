from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Date, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    registration_no = Column(String)
    tax_id = Column(String)
    currency = Column(String, default="ZMW")
    address = Column(Text)
    phone = Column(String)
    email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    subscription_plan = Column(String, default="trial")
    subscription_status = Column(String, default="active")
    trial_ends_at = Column(DateTime)
    subscription_ends_at = Column(DateTime)
    
    users = relationship("User", back_populates="company")
    employees = relationship("Employee", back_populates="company")
    accounts = relationship("Account", back_populates="company")
    journals = relationship("JournalEntry", back_populates="company")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String)
    role = Column(String, default="user")
    company_id = Column(String, ForeignKey("companies.id"), nullable=True)
    is_super_admin = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    company = relationship("Company", back_populates="users")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    user_email = Column(String)  # Cached for deleted users
    action = Column(String, nullable=False, index=True)  # CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, etc.
    entity_type = Column(String, index=True)  # Invoice, Employee, Product, etc.
    entity_id = Column(String, index=True)
    changes = Column(JSON)  # Before/after state
    ip_address = Column(String)
    user_agent = Column(Text)
    status = Column(String, default="success")  # success, failure, error
    error_message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    
    # Relationships
    company = relationship("Company")
    user = relationship("User")

class Department(Base):
    __tablename__ = "departments"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    dept_code = Column(String, nullable=False, index=True)
    dept_name = Column(String, nullable=False)
    parent_dept_id = Column(String, ForeignKey("departments.id"))
    manager_id = Column(String, ForeignKey("users.id"))
    cost_center_code = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    parent_dept = relationship("Department", remote_side=[id], backref="sub_departments")

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    employee_no = Column(String, nullable=False, index=True)
    
    # Personal Information
    first_name = Column(String, nullable=False)
    middle_name = Column(String)
    last_name = Column(String, nullable=False)
    maiden_name = Column(String)  # For labour law compliance
    
    # Contact Details
    email = Column(String, index=True)
    phone = Column(String)
    mobile_phone = Column(String)
    emergency_contact_name = Column(String)
    emergency_contact_phone = Column(String)
    emergency_contact_relationship = Column(String)
    
    # Personal Details
    id_number = Column(String, unique=True, index=True)  # National ID
    passport_number = Column(String)
    drivers_license = Column(String)
    date_of_birth = Column(Date)
    place_of_birth = Column(String)
    gender = Column(String)
    marital_status = Column(String)  # single, married, divorced, widowed
    nationality = Column(String, default="Zambian")
    
    # Address
    residential_address = Column(Text)
    postal_address = Column(String)
    city = Column(String)
    province = Column(String)
    postal_code = Column(String)
    
    # Employment Details
    position = Column(String)
    job_title = Column(String)
    department_id = Column(String, ForeignKey("departments.id"))
    supervisor_id = Column(String, ForeignKey("employees.id"))
    branch_id = Column(String, ForeignKey("branches.id"))
    
    # Employment Dates
    date_joined = Column(Date, index=True)
    probation_period_months = Column(Integer, default=3)
    probation_end_date = Column(Date)
    confirmation_date = Column(Date)  # Permanent confirmation after probation
    contract_end_date = Column(Date)  # For fixed-term contracts
    retirement_date = Column(Date)  # Auto-calculated based on retirement age
    date_terminated = Column(Date)
    termination_reason = Column(String)
    
    # Employment Status & Type
    employment_status = Column(String, default="active", index=True)  # active, probation, suspended, terminated, retired
    employment_type = Column(String, default="permanent")  # permanent, contract, part_time, casual
    work_schedule = Column(String, default="full_time")  # full_time, part_time, shift
    
    # Compensation
    salary_base = Column(Float, default=0.0)
    salary_currency = Column(String, default="ZMW")
    payment_frequency = Column(String, default="monthly")  # monthly, weekly, daily
    payment_method = Column(String, default="bank_transfer")  # bank_transfer, cash, mobile_money
    
    # Banking Details
    bank_name = Column(String)
    bank_account = Column(String)
    bank_branch = Column(String)
    bank_swift_code = Column(String)
    mobile_money_provider = Column(String)  # MTN, Airtel, Zamtel
    mobile_money_number = Column(String)
    
    # Tax & Statutory IDs - CRITICAL FOR ZAMBIAN COMPLIANCE
    tax_id = Column(String, unique=True, index=True)  # TPIN - Tax Payer Identification Number
    napsa_number = Column(String, unique=True, index=True)  # NAPSA (National Pension Scheme Authority) number
    nhima_number = Column(String, unique=True, index=True)  # NHIMA (National Health Insurance) number
    workers_comp_number = Column(String, index=True)  # Workers Compensation Fund number
    
    # Statutory Configuration
    napsa_exempted = Column(Boolean, default=False)  # Some employees may be exempt
    nhima_exempted = Column(Boolean, default=False)
    paye_exempted = Column(Boolean, default=False)
    
    # Labour Law Compliance Fields
    has_employment_contract = Column(Boolean, default=False)
    contract_signed_date = Column(Date)
    labour_card_number = Column(String)  # For foreign workers
    work_permit_number = Column(String)  # For foreign workers
    work_permit_expiry = Column(Date)
    
    # Benefits & Entitlements
    leave_days_annual = Column(Integer, default=24)  # Zambia: 24 days/year
    leave_days_accrued = Column(Float, default=0.0)
    leave_days_taken = Column(Float, default=0.0)
    leave_days_balance = Column(Float, default=0.0)
    sick_leave_days = Column(Integer, default=0)
    maternity_leave_eligible = Column(Boolean, default=False)
    paternity_leave_eligible = Column(Boolean, default=False)
    
    # Skills & Qualifications
    education_level = Column(String)  # Primary, Secondary, Diploma, Degree, Masters, PhD
    qualifications = Column(JSON)  # List of qualifications
    professional_certifications = Column(JSON)
    skills_json = Column(JSON)  # Skills tracking
    
    # Dependents (for benefits & tax relief)
    number_of_dependents = Column(Integer, default=0)
    dependents_json = Column(JSON)  # Detailed dependent information
    
    # Performance & Development
    last_appraisal_date = Column(Date)
    next_appraisal_due = Column(Date)
    performance_rating = Column(String)  # Excellent, Good, Satisfactory, Needs Improvement
    
    # Onboarding & Offboarding
    onboarding_completed = Column(Boolean, default=False)
    onboarding_completion_date = Column(Date)
    onboarding_checklist = Column(JSON)  # Track onboarding tasks
    offboarding_checklist = Column(JSON)  # Track exit tasks
    
    # Documents
    photo_path = Column(String)
    cv_path = Column(String)
    id_document_path = Column(String)
    tax_clearance_path = Column(String)
    educational_certificates_path = Column(JSON)  # Multiple files
    
    # System Fields
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Additional Data
    notes = Column(Text)
    extra_data = Column(JSON)  # Additional flexible data (renamed from 'metadata' to avoid SQLAlchemy conflict)
    
    # Relationships
    company = relationship("Company", back_populates="employees")
    department = relationship("Department")
    supervisor = relationship("Employee", remote_side=[id], foreign_keys=[supervisor_id])
    creator = relationship("User", foreign_keys=[created_by])

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    parent_id = Column(String, ForeignKey("accounts.id"))
    currency = Column(String)  # If set, this account is in foreign currency
    allow_fx_revaluation = Column(Boolean, default=False)  # Enable FX revaluation
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="accounts")
    parent = relationship("Account", remote_side=[id], backref="children")
    journal_lines = relationship("JournalLine", back_populates="account")

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id"))
    branch_id = Column(String, ForeignKey("branches.id"))
    journal_number = Column(String, nullable=False, unique=True)
    date = Column(Date, nullable=False)
    description = Column(Text)
    currency = Column(String, default="ZMW")
    total_amount = Column(Float, nullable=False)
    status = Column(String, default="draft")
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="journals")
    department = relationship("Department")
    lines = relationship("JournalLine", back_populates="journal")

class JournalLine(Base):
    __tablename__ = "journal_lines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    journal_id = Column(String, ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    side = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    narration = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    journal = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="journal_lines")


class ApprovalRequest(Base):
    """
    Approval requests for finance documents (journal entries, invoices, bills, payments)
    Implements approval workflow: draft → pending → approved/rejected → posted → locked
    """
    __tablename__ = "approval_requests"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    document_type = Column(String, nullable=False)  # journal_entry, invoice, bill, payment
    document_id = Column(String, nullable=False)
    requested_by = Column(String, ForeignKey("users.id"), nullable=False)
    approved_by = Column(String, ForeignKey("users.id"))
    approval_level = Column(String, nullable=False)  # basic, medium, high
    status = Column(String, default="pending")  # pending, approved, rejected, cancelled
    notes = Column(Text)  # Submission notes
    approval_notes = Column(Text)  # Approval/rejection notes
    requested_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company")
    requester = relationship("User", foreign_keys=[requested_by])
    approver = relationship("User", foreign_keys=[approved_by])


class Product(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)
    unit_of_measure = Column(String, default="Unit")
    unit_price = Column(Float, default=0.0)
    cost_price = Column(Float, default=0.0)
    reorder_level = Column(Float, default=0.0)
    product_type = Column(String, default="storable")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    stock_items = relationship("StockItem", back_populates="product")

class Warehouse(Base):
    __tablename__ = "warehouses"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    location = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    stock_items = relationship("StockItem", back_populates="warehouse")

class StockItem(Base):
    __tablename__ = "stock_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(String, ForeignKey("warehouses.id"), nullable=False)
    quantity_on_hand = Column(Float, default=0.0)
    reserved_quantity = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="stock_items")
    warehouse = relationship("Warehouse", back_populates="stock_items")

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    customer_code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    tax_id = Column(String)
    address = Column(Text)
    credit_limit = Column(Float, default=0.0)
    payment_terms = Column(String, default="Net 30")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sales_orders = relationship("SalesOrder", back_populates="customer")

class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    supplier_code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    tax_id = Column(String)
    address = Column(Text)
    payment_terms = Column(String, default="Net 30")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id"))
    branch_id = Column(String, ForeignKey("branches.id"))
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False)
    po_number = Column(String, nullable=False, unique=True, index=True)
    order_date = Column(Date, nullable=False)
    expected_delivery = Column(Date)
    status = Column(String, default="draft")
    total_amount = Column(Float, default=0.0)
    notes = Column(Text)
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    supplier = relationship("Supplier", back_populates="purchase_orders")
    department = relationship("Department")
    lines = relationship("PurchaseOrderLine", back_populates="purchase_order")

class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    purchase_order_id = Column(String, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    purchase_order = relationship("PurchaseOrder", back_populates="lines")
    product = relationship("Product")

class SalesOrder(Base):
    __tablename__ = "sales_orders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id"))
    branch_id = Column(String, ForeignKey("branches.id"))
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    so_number = Column(String, nullable=False, unique=True, index=True)
    order_date = Column(Date, nullable=False)
    delivery_date = Column(Date)
    status = Column(String, default="draft")
    total_amount = Column(Float, default=0.0)
    notes = Column(Text)
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="sales_orders")
    department = relationship("Department")
    lines = relationship("SalesOrderLine", back_populates="sales_order")

class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    sales_order_id = Column(String, ForeignKey("sales_orders.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    sales_order = relationship("SalesOrder", back_populates="lines")
    product = relationship("Product")

class LeaveType(Base):
    __tablename__ = "leave_types"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    annual_allocation = Column(Float, default=0.0)
    is_paid = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LeaveApplication(Base):
    __tablename__ = "leave_applications"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    leave_type_id = Column(String, ForeignKey("leave_types.id"), nullable=False)
    application_number = Column(String, nullable=False, unique=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_requested = Column(Float, nullable=False)
    reason = Column(Text)
    status = Column(String, default="pending")
    approved_by = Column(String)
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    employee = relationship("Employee")
    leave_type = relationship("LeaveType")

class MobileMoneyProvider(Base):
    __tablename__ = "mobile_money_providers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    provider_name = Column(String, nullable=False)
    provider_code = Column(String, nullable=False)
    api_key = Column(String)
    api_secret = Column(String)
    merchant_id = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MobileMoneyTransaction(Base):
    __tablename__ = "mobile_money_transactions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    provider_id = Column(String, ForeignKey("mobile_money_providers.id"), nullable=False)
    transaction_ref = Column(String, nullable=False, unique=True, index=True)
    transaction_type = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="ZMW")
    status = Column(String, default="pending")
    external_ref = Column(String)
    customer_name = Column(String)
    description = Column(Text)
    initiated_by = Column(String, ForeignKey("users.id"))
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    provider = relationship("MobileMoneyProvider")

class Branch(Base):
    __tablename__ = "branches"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    branch_code = Column(String, nullable=False, index=True)
    branch_name = Column(String, nullable=False)
    address = Column(Text)
    city = Column(String)
    phone = Column(String)
    email = Column(String)
    manager_id = Column(String, ForeignKey("employees.id"))
    is_active = Column(Boolean, default=True)
    is_main_branch = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    manager = relationship("Employee", foreign_keys=[manager_id])

class BranchStock(Base):
    __tablename__ = "branch_stock"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    branch_id = Column(String, ForeignKey("branches.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, default=0.0)
    reorder_level = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    branch = relationship("Branch")
    product = relationship("Product")

class BranchTransfer(Base):
    __tablename__ = "branch_transfers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    transfer_number = Column(String, nullable=False, unique=True)
    from_branch_id = Column(String, ForeignKey("branches.id"), nullable=False)
    to_branch_id = Column(String, ForeignKey("branches.id"), nullable=False)
    transfer_date = Column(Date, nullable=False)
    status = Column(String, default="pending")
    notes = Column(Text)
    initiated_by = Column(String, ForeignKey("users.id"))
    approved_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    from_branch = relationship("Branch", foreign_keys=[from_branch_id])
    to_branch = relationship("Branch", foreign_keys=[to_branch_id])

class BranchTransferLine(Base):
    __tablename__ = "branch_transfer_lines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    transfer_id = Column(String, ForeignKey("branch_transfers.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    received_quantity = Column(Float, default=0.0)
    
    transfer = relationship("BranchTransfer")
    product = relationship("Product")

class POSTerminal(Base):
    __tablename__ = "pos_terminals"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    branch_id = Column(String, ForeignKey("branches.id"))
    terminal_code = Column(String, nullable=False, unique=True)
    terminal_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    branch = relationship("Branch")

class POSSale(Base):
    __tablename__ = "pos_sales"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    branch_id = Column(String, ForeignKey("branches.id"))
    terminal_id = Column(String, ForeignKey("pos_terminals.id"))
    receipt_number = Column(String, nullable=False, unique=True)
    sale_date = Column(DateTime, default=datetime.utcnow)
    customer_id = Column(String, ForeignKey("customers.id"))
    total_amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    payment_method = Column(String, nullable=False)
    payment_ref = Column(String)
    cashier_id = Column(String, ForeignKey("users.id"))
    status = Column(String, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    branch = relationship("Branch")
    terminal = relationship("POSTerminal")
    customer = relationship("Customer")

class POSSaleLine(Base):
    __tablename__ = "pos_sale_lines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    sale_id = Column(String, ForeignKey("pos_sales.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount = Column(Float, default=0.0)
    subtotal = Column(Float, nullable=False)
    
    sale = relationship("POSSale")
    product = relationship("Product")

class CashierSession(Base):
    __tablename__ = "cashier_sessions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    terminal_id = Column(String, ForeignKey("pos_terminals.id"), nullable=False)
    cashier_id = Column(String, ForeignKey("users.id"), nullable=False)
    session_start = Column(DateTime, default=datetime.utcnow)
    session_end = Column(DateTime)
    opening_cash = Column(Float, default=0.0)
    closing_cash = Column(Float)
    expected_cash = Column(Float)
    variance = Column(Float)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    terminal = relationship("POSTerminal")

class StatutoryObligationTemplate(Base):
    __tablename__ = "statutory_obligation_templates"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    obligation_type = Column(String, nullable=False, unique=True)
    description = Column(Text)
    frequency = Column(String, nullable=False)
    due_day = Column(Integer)
    calculation_method = Column(Text)  # How to calculate the amount
    penalty_rate = Column(Float)  # Penalty percentage for late payment
    authority = Column(String)  # ZRA, NAPSA, NHIMA, etc.
    enabled_by_default = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Currency(Base):
    __tablename__ = "currencies"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    code = Column(String, nullable=False, index=True)  # ISO 4217 code (USD, EUR, GBP, ZMW)
    name = Column(String, nullable=False)
    symbol = Column(String)
    decimal_places = Column(Integer, default=2)
    is_active = Column(Boolean, default=True)
    is_base_currency = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    from_currency = Column(String, nullable=False)  # Base currency
    to_currency = Column(String, nullable=False)  # Foreign currency
    rate = Column(Float, nullable=False)  # 1 base = rate foreign
    rate_date = Column(Date, nullable=False, index=True)
    rate_type = Column(String, default="spot")  # spot, average, budget
    source = Column(String)  # manual, bank_of_zambia, api
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))

class FXRevaluation(Base):
    __tablename__ = "fx_revaluations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    revaluation_date = Column(Date, nullable=False)
    currency = Column(String, nullable=False)
    total_gain_loss = Column(Float, default=0.0)
    journal_entry_id = Column(String, ForeignKey("journal_entries.id"))
    status = Column(String, default="draft")  # draft, posted, reversed
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    journal_entry = relationship("JournalEntry")

class FXRevaluationLine(Base):
    __tablename__ = "fx_revaluation_lines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    revaluation_id = Column(String, ForeignKey("fx_revaluations.id"), nullable=False)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    account_currency = Column(String, nullable=False)
    original_balance = Column(Float, nullable=False)  # In foreign currency
    exchange_rate_old = Column(Float, nullable=False)
    exchange_rate_new = Column(Float, nullable=False)
    balance_base_old = Column(Float, nullable=False)  # In base currency
    balance_base_new = Column(Float, nullable=False)  # In base currency
    gain_loss = Column(Float, nullable=False)  # Positive = gain, Negative = loss
    created_at = Column(DateTime, default=datetime.utcnow)
    
    revaluation = relationship("FXRevaluation")
    account = relationship("Account")

class BankAccount(Base):
    __tablename__ = "bank_accounts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)  # Links to Chart of Accounts
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    account_name = Column(String)
    branch = Column(String)
    currency = Column(String, default="ZMW")
    swift_code = Column(String)
    is_active = Column(Boolean, default=True)
    last_reconciled_date = Column(Date)
    last_reconciled_balance = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    account = relationship("Account")

class BankStatement(Base):
    __tablename__ = "bank_statements"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    bank_account_id = Column(String, ForeignKey("bank_accounts.id"), nullable=False)
    statement_number = Column(String, nullable=False)
    statement_date = Column(Date, nullable=False)
    opening_balance = Column(Float, default=0.0)
    closing_balance = Column(Float, default=0.0)
    status = Column(String, default="draft")  # draft, imported, reconciled
    import_source = Column(String)  # manual, csv, api, ocr
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    bank_account = relationship("BankAccount")
    lines = relationship("BankStatementLine", back_populates="statement")

class BankStatementLine(Base):
    __tablename__ = "bank_statement_lines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    statement_id = Column(String, ForeignKey("bank_statements.id"), nullable=False)
    line_number = Column(Integer, nullable=False)
    transaction_date = Column(Date, nullable=False)
    value_date = Column(Date)
    description = Column(Text, nullable=False)
    reference = Column(String)
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    balance = Column(Float)
    is_matched = Column(Boolean, default=False)
    matched_journal_line_id = Column(String, ForeignKey("journal_lines.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    statement = relationship("BankStatement", back_populates="lines")
    matched_journal_line = relationship("JournalLine")

class BankReconciliation(Base):
    __tablename__ = "bank_reconciliations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    bank_account_id = Column(String, ForeignKey("bank_accounts.id"), nullable=False)
    reconciliation_number = Column(String, nullable=False, unique=True)
    reconciliation_date = Column(Date, nullable=False)
    statement_id = Column(String, ForeignKey("bank_statements.id"))
    opening_balance_bank = Column(Float, default=0.0)
    closing_balance_bank = Column(Float, default=0.0)
    opening_balance_book = Column(Float, default=0.0)
    closing_balance_book = Column(Float, default=0.0)
    total_matched_debits = Column(Float, default=0.0)
    total_matched_credits = Column(Float, default=0.0)
    total_unmatched_debits_bank = Column(Float, default=0.0)
    total_unmatched_credits_bank = Column(Float, default=0.0)
    total_unmatched_debits_book = Column(Float, default=0.0)
    total_unmatched_credits_book = Column(Float, default=0.0)
    status = Column(String, default="in_progress")  # in_progress, completed, approved
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    completed_at = Column(DateTime)
    approved_at = Column(DateTime)
    approved_by = Column(String, ForeignKey("users.id"))
    
    bank_account = relationship("BankAccount")
    statement = relationship("BankStatement")
    matches = relationship("BankReconciliationMatch", back_populates="reconciliation")

class BankReconciliationMatch(Base):
    __tablename__ = "bank_reconciliation_matches"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    reconciliation_id = Column(String, ForeignKey("bank_reconciliations.id"), nullable=False)
    statement_line_id = Column(String, ForeignKey("bank_statement_lines.id"))
    journal_line_id = Column(String, ForeignKey("journal_lines.id"))
    match_type = Column(String, default="manual")  # auto, manual, suggested
    match_confidence = Column(Float)  # 0.0 to 1.0 for auto-match confidence
    amount = Column(Float, nullable=False)
    matched_at = Column(DateTime, default=datetime.utcnow)
    matched_by = Column(String, ForeignKey("users.id"))
    
    reconciliation = relationship("BankReconciliation", back_populates="matches")
    statement_line = relationship("BankStatementLine")
    journal_line = relationship("JournalLine")

class FixedAsset(Base):
    __tablename__ = "fixed_assets"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    asset_code = Column(String, nullable=False, index=True)
    asset_name = Column(String, nullable=False)
    asset_category = Column(String, nullable=False)  # Building, Vehicle, Equipment, Furniture, IT
    description = Column(Text)
    purchase_date = Column(Date, nullable=False)
    purchase_cost = Column(Float, nullable=False)
    residual_value = Column(Float, default=0.0)
    useful_life_years = Column(Integer, nullable=False)
    depreciation_method = Column(String, default="straight_line")  # straight_line, reducing_balance
    depreciation_rate = Column(Float)  # For reducing balance method
    accumulated_depreciation = Column(Float, default=0.0)
    book_value = Column(Float)
    location = Column(String)
    custodian = Column(String)
    serial_number = Column(String)
    asset_account_id = Column(String, ForeignKey("accounts.id"))
    depreciation_account_id = Column(String, ForeignKey("accounts.id"))
    accumulated_depreciation_account_id = Column(String, ForeignKey("accounts.id"))
    status = Column(String, default="active")  # active, disposed, written_off
    disposal_date = Column(Date)
    disposal_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    asset_account = relationship("Account", foreign_keys=[asset_account_id])
    depreciation_account = relationship("Account", foreign_keys=[depreciation_account_id])
    accumulated_dep_account = relationship("Account", foreign_keys=[accumulated_depreciation_account_id])

class DepreciationSchedule(Base):
    __tablename__ = "depreciation_schedules"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    asset_id = Column(String, ForeignKey("fixed_assets.id"), nullable=False)
    period_month = Column(Integer, nullable=False)
    period_year = Column(Integer, nullable=False)
    opening_book_value = Column(Float, nullable=False)
    depreciation_amount = Column(Float, nullable=False)
    closing_book_value = Column(Float, nullable=False)
    journal_entry_id = Column(String, ForeignKey("journal_entries.id"))
    status = Column(String, default="draft")  # draft, posted
    created_at = Column(DateTime, default=datetime.utcnow)
    
    asset = relationship("FixedAsset")
    journal_entry = relationship("JournalEntry")

class AccountingPeriod(Base):
    __tablename__ = "accounting_periods"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    period_name = Column(String, nullable=False)  # e.g., "January 2025", "Q1 2025"
    period_type = Column(String, default="monthly")  # monthly, quarterly, yearly
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    status = Column(String, default="open")  # open, closed, locked
    close_notes = Column(Text)
    closed_at = Column(DateTime)
    closed_by = Column(String, ForeignKey("users.id"))
    lock_notes = Column(Text)
    locked_at = Column(DateTime)
    locked_by = Column(String, ForeignKey("users.id"))
    reopen_reason = Column(Text)
    reopened_at = Column(DateTime)
    reopened_by = Column(String, ForeignKey("users.id"))
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company")
    closer = relationship("User", foreign_keys=[closed_by])
    locker = relationship("User", foreign_keys=[locked_by])
    reopener = relationship("User", foreign_keys=[reopened_by])
    creator = relationship("User", foreign_keys=[created_by])

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    invoice_number = Column(String, nullable=False, unique=True, index=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    currency = Column(String, default="ZMW")
    subtotal = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    status = Column(String, default="draft")  # draft, sent, paid, overdue, cancelled
    # Smart Invoice / ZRA Compliance fields
    qr_code = Column(Text)  # QR code for ZRA compliance
    ubl_xml = Column(Text)  # UBL (Universal Business Language) XML format
    zra_reference = Column(String)  # ZRA validation reference
    zra_validated = Column(Boolean, default=False)
    zra_validated_at = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    customer = relationship("Customer")

class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"))
    description = Column(Text, nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.0)
    line_total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    invoice = relationship("Invoice")
    product = relationship("Product")

class Operation(Base):
    __tablename__ = "operations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    operation_code = Column(String, nullable=False, index=True)
    operation_name = Column(String, nullable=False)
    operation_type = Column(String, nullable=False)  # manufacturing, agriculture, food_processing, assembly
    description = Column(Text)
    output_product_id = Column(String, ForeignKey("products.id"))  # Main output product
    standard_output_quantity = Column(Float, default=1.0)
    standard_duration_hours = Column(Float)  # Expected duration
    department_id = Column(String, ForeignKey("departments.id"))
    cost_center_id = Column(String, ForeignKey("accounts.id"))  # For cost allocation
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    output_product = relationship("Product")
    department = relationship("Department")
    steps = relationship("OperationStep", back_populates="operation")

class OperationStep(Base):
    __tablename__ = "operation_steps"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    operation_id = Column(String, ForeignKey("operations.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_name = Column(String, nullable=False)
    description = Column(Text)
    duration_hours = Column(Float)
    labor_cost_per_hour = Column(Float, default=0.0)
    machine_cost_per_hour = Column(Float, default=0.0)
    overhead_rate = Column(Float, default=0.0)  # Percentage
    is_quality_control = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    operation = relationship("Operation", back_populates="steps")

class Batch(Base):
    __tablename__ = "batches"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    batch_number = Column(String, nullable=False, unique=True, index=True)
    operation_id = Column(String, ForeignKey("operations.id"), nullable=False)
    planned_quantity = Column(Float, nullable=False)
    actual_quantity = Column(Float, default=0.0)
    unit_of_measure = Column(String, default="units")
    start_date = Column(DateTime)
    planned_end_date = Column(DateTime)
    actual_end_date = Column(DateTime)
    status = Column(String, default="draft")  # draft, planned, in_progress, completed, cancelled
    department_id = Column(String, ForeignKey("departments.id"))
    branch_id = Column(String, ForeignKey("branches.id"))
    supervisor_id = Column(String, ForeignKey("employees.id"))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    operation = relationship("Operation")
    department = relationship("Department")
    branch = relationship("Branch")
    inputs = relationship("BatchInput", back_populates="batch")
    outputs = relationship("BatchOutput", back_populates="batch")
    costs = relationship("BatchCost", back_populates="batch")

class BatchInput(Base):
    __tablename__ = "batch_inputs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    planned_quantity = Column(Float, nullable=False)
    actual_quantity = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    warehouse_id = Column(String, ForeignKey("warehouses.id"))
    issued_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    batch = relationship("Batch", back_populates="inputs")
    product = relationship("Product")
    warehouse = relationship("Warehouse")

class BatchOutput(Base):
    __tablename__ = "batch_outputs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    output_type = Column(String, default="finished_good")  # finished_good, by_product, waste
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, default=0.0)  # Calculated from batch costs
    total_cost = Column(Float, default=0.0)
    warehouse_id = Column(String, ForeignKey("warehouses.id"))
    received_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    batch = relationship("Batch", back_populates="outputs")
    product = relationship("Product")
    warehouse = relationship("Warehouse")

class BatchCost(Base):
    __tablename__ = "batch_costs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False)
    cost_type = Column(String, nullable=False)  # material, labor, overhead, machine
    description = Column(String)
    amount = Column(Float, nullable=False)
    account_id = Column(String, ForeignKey("accounts.id"))  # For GL posting
    posted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    batch = relationship("Batch", back_populates="costs")
    account = relationship("Account")

class TransferPrice(Base):
    __tablename__ = "transfer_prices"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    from_department_id = Column(String, ForeignKey("departments.id"))
    to_department_id = Column(String, ForeignKey("departments.id"))
    from_branch_id = Column(String, ForeignKey("branches.id"))
    to_branch_id = Column(String, ForeignKey("branches.id"))
    pricing_method = Column(String, default="cost_plus")  # cost_plus, market_price, negotiated
    cost_price = Column(Float, default=0.0)
    markup_percentage = Column(Float, default=0.0)  # For cost_plus method
    transfer_price = Column(Float, nullable=False)
    margin_amount = Column(Float, default=0.0)  # Calculated margin
    margin_percentage = Column(Float, default=0.0)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    product = relationship("Product")
    from_department = relationship("Department", foreign_keys=[from_department_id])
    to_department = relationship("Department", foreign_keys=[to_department_id])
    from_branch = relationship("Branch", foreign_keys=[from_branch_id])
    to_branch = relationship("Branch", foreign_keys=[to_branch_id])

class TransferOrder(Base):
    __tablename__ = "transfer_orders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    transfer_number = Column(String, nullable=False, unique=True, index=True)
    from_department_id = Column(String, ForeignKey("departments.id"))
    to_department_id = Column(String, ForeignKey("departments.id"))
    from_branch_id = Column(String, ForeignKey("branches.id"))
    to_branch_id = Column(String, ForeignKey("branches.id"))
    from_warehouse_id = Column(String, ForeignKey("warehouses.id"))
    to_warehouse_id = Column(String, ForeignKey("warehouses.id"))
    transfer_date = Column(Date, nullable=False)
    total_cost = Column(Float, default=0.0)  # Total cost from sending department
    total_transfer_price = Column(Float, default=0.0)  # Total price charged to receiving department
    total_margin = Column(Float, default=0.0)  # Total margin (profit to sending department)
    status = Column(String, default="draft")  # draft, approved, in_transit, received, cancelled
    approved_by = Column(String, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    received_by = Column(String, ForeignKey("users.id"))
    received_at = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    from_department = relationship("Department", foreign_keys=[from_department_id])
    to_department = relationship("Department", foreign_keys=[to_department_id])
    from_branch = relationship("Branch", foreign_keys=[from_branch_id])
    to_branch = relationship("Branch", foreign_keys=[to_branch_id])
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
    lines = relationship("TransferOrderLine", back_populates="transfer_order")

class TransferOrderLine(Base):
    __tablename__ = "transfer_order_lines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    transfer_order_id = Column(String, ForeignKey("transfer_orders.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, default=0.0)  # Cost to sending department
    transfer_price = Column(Float, default=0.0)  # Price charged to receiving department
    margin_amount = Column(Float, default=0.0)  # Calculated margin per line
    margin_percentage = Column(Float, default=0.0)
    line_total_cost = Column(Float, default=0.0)
    line_total_price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transfer_order = relationship("TransferOrder", back_populates="lines")
    product = relationship("Product")

class WIPBalance(Base):
    __tablename__ = "wip_balances"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"))
    operation_id = Column(String, ForeignKey("operations.id"))
    department_id = Column(String, ForeignKey("departments.id"))
    branch_id = Column(String, ForeignKey("branches.id"))
    as_of_date = Column(Date, nullable=False)
    material_cost = Column(Float, default=0.0)
    labor_cost = Column(Float, default=0.0)
    overhead_cost = Column(Float, default=0.0)
    machine_cost = Column(Float, default=0.0)
    total_wip_value = Column(Float, default=0.0)
    quantity_in_progress = Column(Float, default=0.0)
    batch_count = Column(Integer, default=0)  # Number of batches in WIP
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    product = relationship("Product")
    operation = relationship("Operation")
    department = relationship("Department")
    branch = relationship("Branch")

class IndustryTemplate(Base):
    __tablename__ = "industry_templates"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    template_code = Column(String, nullable=False, unique=True, index=True)
    template_name = Column(String, nullable=False)
    industry_type = Column(String, nullable=False)  # agriculture, manufacturing, retail, services, etc.
    description = Column(Text)
    template_config = Column(JSON)  # Stores operations, products, accounts, workflows as JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CompanyIndustryTemplate(Base):
    __tablename__ = "company_industry_templates"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    template_id = Column(String, ForeignKey("industry_templates.id"), nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow)
    applied_by = Column(String, ForeignKey("users.id"))
    customizations = Column(JSON)  # Stores any company-specific modifications
    
    company = relationship("Company")
    template = relationship("IndustryTemplate")

class DocumentUpload(Base):
    __tablename__ = "document_uploads"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    document_type = Column(String, nullable=False)  # invoice, receipt, purchase_order, contract, etc.
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Storage path
    file_size = Column(Integer)  # File size in bytes
    mime_type = Column(String)
    uploaded_by = Column(String, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    ocr_status = Column(String, default="pending")  # pending, processing, completed, failed
    ocr_processed_at = Column(DateTime)
    notes = Column(Text)
    
    company = relationship("Company")

class OCRResult(Base):
    __tablename__ = "ocr_results"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("document_uploads.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    extracted_text = Column(Text)  # Raw OCR text
    structured_data = Column(JSON)  # AI-extracted structured data
    confidence_score = Column(Float)  # Overall confidence (0-100)
    ai_model = Column(String, default="claude-3.5-sonnet")
    processing_time_ms = Column(Integer)
    validation_status = Column(String, default="pending")  # pending, approved, rejected, needs_review
    validated_by = Column(String, ForeignKey("users.id"))
    validated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("DocumentUpload")

class ExtractedInvoiceData(Base):
    __tablename__ = "extracted_invoice_data"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    ocr_result_id = Column(String, ForeignKey("ocr_results.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    # Supplier Information
    supplier_name = Column(String)
    supplier_tax_id = Column(String)
    supplier_address = Column(Text)
    supplier_phone = Column(String)
    supplier_email = Column(String)
    
    # Invoice Details
    invoice_number = Column(String, index=True)
    invoice_date = Column(Date)
    due_date = Column(Date)
    purchase_order_number = Column(String)
    
    # Financial Information
    currency = Column(String, default="ZMW")
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    amount_due = Column(Float, default=0.0)
    
    # Line Items
    line_items = Column(JSON)  # Array of {description, quantity, unit_price, amount}
    
    # Matching & Status
    matched_supplier_id = Column(String, ForeignKey("suppliers.id"))  # Auto-matched supplier
    match_confidence = Column(Float)
    created_invoice_id = Column(String)  # If invoice was auto-created
    status = Column(String, default="extracted")  # extracted, matched, imported, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    
    ocr_result = relationship("OCRResult")
    matched_supplier = relationship("Supplier")

class ExtractedReceiptData(Base):
    __tablename__ = "extracted_receipt_data"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    ocr_result_id = Column(String, ForeignKey("ocr_results.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    # Merchant Information
    merchant_name = Column(String)
    merchant_address = Column(Text)
    merchant_phone = Column(String)
    merchant_tax_id = Column(String)
    
    # Receipt Details
    receipt_number = Column(String, index=True)
    receipt_date = Column(Date)
    receipt_time = Column(String)
    
    # Financial Information
    currency = Column(String, default="ZMW")
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    tip_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    
    # Payment Information
    payment_method = Column(String)  # cash, card, mobile_money, etc.
    card_last_four = Column(String)
    
    # Line Items
    line_items = Column(JSON)  # Array of {description, quantity, unit_price, amount}
    
    # Categorization
    expense_category = Column(String)  # AI-suggested category
    category_confidence = Column(Float)
    created_expense_id = Column(String)  # If expense was auto-created
    status = Column(String, default="extracted")  # extracted, categorized, imported, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    
    ocr_result = relationship("OCRResult")

class EmploymentContract(Base):
    __tablename__ = "employment_contracts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    contract_number = Column(String, nullable=False, unique=True, index=True)
    contract_type = Column(String, nullable=False)  # permanent, fixed_term, probation, contract, internship
    position_title = Column(String, nullable=False)
    department_id = Column(String, ForeignKey("departments.id"))
    reporting_to_id = Column(String, ForeignKey("employees.id"))  # Supervisor
    
    # Contract Terms
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)  # For fixed-term contracts
    probation_period_months = Column(Integer, default=3)
    notice_period_days = Column(Integer, default=30)
    
    # Compensation
    salary_amount = Column(Float, nullable=False)
    salary_currency = Column(String, default="ZMW")
    salary_frequency = Column(String, default="monthly")  # monthly, bi_weekly, weekly
    bonus_eligible = Column(Boolean, default=False)
    benefits_package = Column(JSON)  # Array of benefits (medical, pension, allowances)
    
    # Work Arrangement
    work_location = Column(String)
    remote_allowed = Column(Boolean, default=False)
    working_hours_per_week = Column(Float, default=40.0)
    
    # Documents
    contract_document_path = Column(String)  # Signed contract file
    signed_by_employee_at = Column(DateTime)
    signed_by_employer_at = Column(DateTime)
    signed_by_employer_id = Column(String, ForeignKey("users.id"))
    
    # Status
    status = Column(String, default="draft")  # draft, active, terminated, expired, renewed
    termination_date = Column(Date)
    termination_reason = Column(Text)
    terminated_by = Column(String, ForeignKey("users.id"))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    employee = relationship("Employee", foreign_keys=[employee_id])
    department = relationship("Department")
    reporting_to = relationship("Employee", foreign_keys=[reporting_to_id])

class EmployeeSkill(Base):
    __tablename__ = "employee_skills"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    skill_name = Column(String, nullable=False)
    skill_category = Column(String)  # technical, soft_skills, language, certification, etc.
    proficiency_level = Column(String)  # beginner, intermediate, advanced, expert
    years_of_experience = Column(Float)
    last_used_date = Column(Date)
    verified_by = Column(String, ForeignKey("users.id"))  # Manager who verified
    verified_at = Column(DateTime)
    certification_name = Column(String)
    certification_number = Column(String)
    certification_expires_at = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    employee = relationship("Employee")
    filled_by_employee = relationship("Employee")

class PerformanceReview(Base):
    __tablename__ = "performance_reviews"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    review_period_start = Column(Date, nullable=False)
    review_period_end = Column(Date, nullable=False)
    review_type = Column(String, default="annual")  # annual, semi_annual, quarterly, probation
    
    # Ratings
    overall_rating = Column(Float)  # 1-5 scale
    performance_rating = Column(Float)  # Job performance
    behavior_rating = Column(Float)  # Conduct and behavior
    goal_achievement_rating = Column(Float)  # Goals met
    
    # Reviews
    strengths = Column(JSON)  # Array of strength points
    areas_for_improvement = Column(JSON)  # Array of improvement areas
    achievements = Column(JSON)  # Key achievements during period
    goals_for_next_period = Column(JSON)  # Goals for next review period
    
    # Feedback
    manager_comments = Column(Text)
    employee_comments = Column(Text)
    hr_comments = Column(Text)
    
    # People Involved
    reviewed_by = Column(String, ForeignKey("users.id"))  # Manager conducting review
    reviewed_at = Column(DateTime)
    acknowledged_by_employee_at = Column(DateTime)
    
    # Outcomes
    promotion_recommended = Column(Boolean, default=False)
    salary_increase_recommended = Column(Boolean, default=False)
    recommended_salary_increase_percent = Column(Float)
    training_recommendations = Column(JSON)
    
    # Status
    status = Column(String, default="draft")  # draft, in_progress, completed, acknowledged
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    employee = relationship("Employee")

class BankConnection(Base):
    __tablename__ = "bank_connections"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    bank_name = Column(String, nullable=False)  # ZANACO, ABSA, FNB, Stanbic
    bank_code = Column(String, nullable=False, index=True)  # zanaco, absa, fnb, stanbic
    account_number = Column(String, nullable=False)
    account_name = Column(String)
    account_type = Column(String)  # savings, current, business
    currency = Column(String, default="ZMW")
    branch_code = Column(String)
    
    # API Credentials (encrypted in production)
    api_username = Column(String)
    api_key_encrypted = Column(String)
    api_endpoint = Column(String)
    
    # Connection Status
    is_active = Column(Boolean, default=True)
    connection_status = Column(String, default="pending")  # pending, connected, failed, disconnected
    last_sync_at = Column(DateTime)
    last_sync_status = Column(String)  # success, failed, partial
    sync_frequency = Column(String, default="daily")  # manual, hourly, daily, weekly
    
    # Auto-sync Settings
    auto_sync_enabled = Column(Boolean, default=True)
    auto_reconcile_enabled = Column(Boolean, default=False)
    
    # Linked Account
    linked_bank_account_id = Column(String, ForeignKey("bank_accounts.id"))  # From Phase 2 bank reconciliation
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    linked_bank_account = relationship("BankAccount")

class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    __table_args__ = (
        UniqueConstraint('bank_connection_id', 'bank_transaction_id', name='uq_bank_connection_transaction'),
    )
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    bank_connection_id = Column(String, ForeignKey("bank_connections.id"), nullable=False)
    
    # Transaction Details from Bank
    bank_transaction_id = Column(String, index=True)  # External bank reference (unique per connection)
    transaction_date = Column(Date, nullable=False)
    posting_date = Column(Date)
    description = Column(Text)
    transaction_type = Column(String)  # debit, credit, fee, interest
    amount = Column(Float, nullable=False)
    balance_after = Column(Float)
    currency = Column(String, default="ZMW")
    
    # Additional Details
    reference_number = Column(String)
    counterparty_name = Column(String)
    counterparty_account = Column(String)
    category = Column(String)  # payment, transfer, withdrawal, deposit, fee
    
    # Reconciliation
    is_reconciled = Column(Boolean, default=False)
    reconciled_with_statement_id = Column(String, ForeignKey("bank_statements.id"))
    reconciled_at = Column(DateTime)
    matched_journal_entry_id = Column(String, ForeignKey("journal_entries.id"))
    
    # AI Categorization
    suggested_account_id = Column(String, ForeignKey("accounts.id"))  # AI-suggested GL account
    suggestion_confidence = Column(Float)
    
    # Import Tracking
    import_batch_id = Column(String)
    imported_at = Column(DateTime, default=datetime.utcnow)
    
    bank_connection = relationship("BankConnection")

class BankSyncHistory(Base):
    __tablename__ = "bank_sync_history"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    bank_connection_id = Column(String, ForeignKey("bank_connections.id"), nullable=False)
    
    sync_type = Column(String, default="manual")  # manual, scheduled, auto
    sync_started_at = Column(DateTime, default=datetime.utcnow)
    sync_completed_at = Column(DateTime)
    
    status = Column(String, default="in_progress")  # in_progress, completed, failed, partial
    
    # Sync Results
    transactions_fetched = Column(Integer, default=0)
    transactions_new = Column(Integer, default=0)
    transactions_updated = Column(Integer, default=0)
    transactions_failed = Column(Integer, default=0)
    
    # Date Range
    from_date = Column(Date)
    to_date = Column(Date)
    
    # Error Tracking
    error_message = Column(Text)
    error_details = Column(JSON)
    
    triggered_by = Column(String, ForeignKey("users.id"))
    
    bank_connection = relationship("BankConnection")

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    setting_key = Column(String, nullable=False, index=True)
    setting_value = Column(Text)
    setting_type = Column(String, default="string")  # string, number, boolean, json
    category = Column(String)  # general, payroll, finance, hr, inventory
    description = Column(Text)
    is_public = Column(Boolean, default=False)  # Can be viewed by non-admins
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, ForeignKey("users.id"))

class EmailTemplate(Base):
    __tablename__ = "email_templates"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    template_name = Column(String, nullable=False)
    template_code = Column(String, nullable=False, index=True)  # payslip, leave_approval, invoice, etc.
    subject = Column(String, nullable=False)
    body_html = Column(Text)  # HTML email body with {{placeholders}}
    body_text = Column(Text)  # Plain text fallback
    
    # Template Variables (JSON array)
    available_variables = Column(JSON)  # ["employee_name", "payslip_date", "amount", etc.]
    
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System templates cannot be deleted
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))

class SalaryComponent(Base):
    __tablename__ = "salary_components"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    component_code = Column(String, nullable=False, index=True)  # BASIC, HRA, TRANSPORT, etc.
    component_name = Column(String, nullable=False)
    component_type = Column(String, nullable=False)  # earning, deduction, benefit
    
    # Calculation
    calculation_method = Column(String, default="fixed")  # fixed, percentage, formula
    default_amount = Column(Float, default=0.0)
    percentage_of = Column(String)  # For percentage: basic, gross, net
    formula = Column(Text)  # For formula: JSON expression
    
    # Tax Treatment
    is_taxable = Column(Boolean, default=True)
    is_pensionable = Column(Boolean, default=False)
    include_in_gross = Column(Boolean, default=True)
    
    # Statutory
    is_statutory = Column(Boolean, default=False)  # PAYE, NAPSA, NHIMA
    statutory_type = Column(String)  # paye, napsa, nhima, pension
    
    # GL Account Mapping
    expense_account_id = Column(String, ForeignKey("accounts.id"))
    payable_account_id = Column(String, ForeignKey("accounts.id"))
    
    # Status
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))

class ApprovalWorkflowRule(Base):
    __tablename__ = "approval_workflow_rules"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    workflow_name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)  # leave_application, loan, purchase_order, journal_entry, etc.
    
    # Conditions (JSON)
    conditions = Column(JSON)  # {amount_min: 0, amount_max: 10000, department: "sales"}
    
    # Approval Chain (JSON array)
    approval_chain = Column(JSON)  # [{level: 1, approver_role: "manager", required: true}, {level: 2, approver_role: "hr_head", required: false}]
    
    # Notification Settings
    notify_on_submit = Column(Boolean, default=True)
    notify_on_approve = Column(Boolean, default=True)
    notify_on_reject = Column(Boolean, default=True)
    escalation_hours = Column(Integer)  # Hours before escalation
    
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Lower number = higher priority
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))

class LeaveTypeConfiguration(Base):
    __tablename__ = "leave_type_configurations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    leave_type_id = Column(String, ForeignKey("leave_types.id"), nullable=False)
    
    # Accrual Settings
    accrual_method = Column(String, default="annual")  # annual, monthly, per_pay_period, none
    accrual_rate = Column(Float, default=0.0)  # Days per period
    max_accrual = Column(Float)  # Maximum accumulated days
    carry_forward_allowed = Column(Boolean, default=True)
    max_carry_forward = Column(Float)  # Maximum days to carry forward
    carry_forward_expiry_months = Column(Integer)  # Months before carried days expire
    
    # Leave Rules
    min_days_per_request = Column(Float, default=0.5)
    max_days_per_request = Column(Float)
    max_consecutive_days = Column(Float)
    requires_approval = Column(Boolean, default=True)
    approval_levels = Column(Integer, default=1)
    
    # Notice Period
    min_notice_days = Column(Integer, default=0)  # Days notice required
    max_advance_days = Column(Integer)  # How far in advance can be requested
    
    # Weekend & Holiday Handling
    exclude_weekends = Column(Boolean, default=True)
    exclude_holidays = Column(Boolean, default=True)
    
    # Documentation
    requires_documents = Column(Boolean, default=False)
    document_types = Column(JSON)  # ["medical_certificate", "travel_docs"]
    
    # Financial
    is_paid = Column(Boolean, default=True)
    pay_percentage = Column(Float, default=100.0)  # % of salary paid
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    leave_type = relationship("LeaveType")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    notification_type = Column(String, default="info")  # info, warning, error, success
    channel = Column(String, default="in_app")  # in_app, email, sms, all
    priority = Column(String, default="normal")  # low, normal, high, urgent
    
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    
    related_entity_type = Column(String)  # leave_application, loan, payslip, invoice, etc.
    related_entity_id = Column(String)
    
    action_url = Column(String)  # URL to navigate to when clicked
    action_label = Column(String)  # Label for action button
    
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)
    
    sms_sent = Column(Boolean, default=False)
    sms_sent_at = Column(DateTime)
    
    expires_at = Column(DateTime)  # Auto-archive after this date
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    user = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by])

class AutoPostingRule(Base):
    __tablename__ = "auto_posting_rules"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    rule_name = Column(String, nullable=False)
    rule_code = Column(String, nullable=False, index=True, unique=True)
    description = Column(Text)
    
    # Rule Trigger Conditions
    source_type = Column(String, nullable=False)  # bank_transaction, mobile_money, invoice_payment, etc.
    transaction_type = Column(String)  # debit, credit, collection, disbursement
    
    # Pattern Matching (JSON) - flexible matching criteria
    match_criteria = Column(JSON)  # {description_contains: "SALARY", counterparty_contains: "ABC LTD", amount_min: 1000}
    
    # Posting Actions (JSON array)
    posting_actions = Column(JSON)  # [{account_id: "xxx", side: "debit", amount_type: "full"}, {account_id: "yyy", side: "credit", amount_type: "full"}]
    
    # Additional Options
    auto_apply = Column(Boolean, default=False)  # Auto-apply without review
    require_approval = Column(Boolean, default=True)
    priority = Column(Integer, default=100)  # Higher priority rules run first
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Usage Stats
    times_matched = Column(Integer, default=0)
    times_applied = Column(Integer, default=0)
    last_matched_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ReconciliationRule(Base):
    __tablename__ = "reconciliation_rules"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    rule_name = Column(String, nullable=False)
    rule_type = Column(String, nullable=False)  # exact_match, fuzzy_match, date_amount_match, ml_match
    description = Column(Text)
    
    # Matching Criteria
    match_on_amount = Column(Boolean, default=True)
    amount_tolerance = Column(Float, default=0.01)  # Allow 1 cent variance
    match_on_date = Column(Boolean, default=True)
    date_tolerance_days = Column(Integer, default=3)  # Allow 3 days variance
    match_on_reference = Column(Boolean, default=False)
    match_on_description = Column(Boolean, default=False)
    description_similarity_threshold = Column(Float, default=0.8)  # 80% similarity
    
    # ML/AI Settings
    use_ml_matching = Column(Boolean, default=False)
    ml_confidence_threshold = Column(Float, default=0.85)  # 85% confidence required
    learn_from_manual_matches = Column(Boolean, default=True)
    
    # Auto-match Settings
    auto_match_enabled = Column(Boolean, default=False)
    auto_match_max_amount = Column(Float)  # Only auto-match below this amount
    require_review = Column(Boolean, default=True)
    
    # Priority
    priority = Column(Integer, default=100)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Usage Stats
    matches_suggested = Column(Integer, default=0)
    matches_accepted = Column(Integer, default=0)
    matches_rejected = Column(Integer, default=0)
    accuracy_rate = Column(Float)  # accepted / suggested
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    payment_number = Column(String, nullable=False, unique=True, index=True)
    payment_date = Column(Date, nullable=False)
    payment_type = Column(String, nullable=False)  # customer_receipt, supplier_payment, expense_payment
    payment_method = Column(String, nullable=False)  # cash, bank_transfer, mobile_money, cheque, card
    
    # Amounts
    amount = Column(Float, nullable=False)
    currency = Column(String, default="ZMW")
    exchange_rate = Column(Float, default=1.0)
    amount_base = Column(Float)  # Amount in base currency
    
    # Related Entities
    customer_id = Column(String, ForeignKey("customers.id"))
    supplier_id = Column(String, ForeignKey("suppliers.id"))
    
    # Payment Source/Destination
    bank_account_id = Column(String, ForeignKey("bank_accounts.id"))
    mobile_money_provider_id = Column(String, ForeignKey("mobile_money_providers.id"))
    cash_account_id = Column(String, ForeignKey("accounts.id"))
    
    # Linked Transactions
    bank_transaction_id = Column(String, ForeignKey("bank_transactions.id"))
    mobile_money_transaction_id = Column(String, ForeignKey("mobile_money_transactions.id"))
    journal_entry_id = Column(String, ForeignKey("journal_entries.id"))
    
    # Additional Details
    reference_number = Column(String)
    description = Column(Text)
    notes = Column(Text)
    
    # Status
    status = Column(String, default="draft")  # draft, submitted, approved, posted, cancelled
    posted_at = Column(DateTime)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    approved_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    customer = relationship("Customer")
    supplier = relationship("Supplier")
    bank_account = relationship("BankAccount")
    mobile_money_provider = relationship("MobileMoneyProvider")
    cash_account = relationship("Account", foreign_keys=[cash_account_id])
    bank_transaction = relationship("BankTransaction")
    mobile_money_transaction = relationship("MobileMoneyTransaction")
    journal_entry = relationship("JournalEntry")

# ============================================================================
# PHASE 2: MANUFACTURING ENGINE
# ============================================================================

class BillOfMaterials(Base):
    """Bill of Materials - defines components needed to manufacture a product"""
    __tablename__ = "bill_of_materials"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    bom_code = Column(String, nullable=False, unique=True, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    version = Column(Integer, default=1)
    quantity_produced = Column(Float, default=1.0)  # Output quantity
    unit_of_measure = Column(String, default="Unit")
    
    # BOM Type
    bom_type = Column(String, default="manufacturing")  # manufacturing, engineering, assembly
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Routing
    routing_id = Column(String, ForeignKey("routings.id"))
    
    # Costing
    total_material_cost = Column(Float, default=0.0)
    total_labor_cost = Column(Float, default=0.0)
    total_overhead_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    routing = relationship("Routing")
    lines = relationship("BOMLine", back_populates="bom", cascade="all, delete-orphan")

class BOMLine(Base):
    """BOM Line - individual component in a BOM"""
    __tablename__ = "bom_lines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    bom_id = Column(String, ForeignKey("bill_of_materials.id"), nullable=False)
    
    line_number = Column(Integer, nullable=False)
    component_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_of_measure = Column(String, default="Unit")
    
    # Scrap/Waste
    scrap_percentage = Column(Float, default=0.0)
    
    # Costing
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Operation (optional - link to specific routing operation)
    operation_id = Column(String, ForeignKey("routing_operations.id"))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    bom = relationship("BillOfMaterials", back_populates="lines")
    component = relationship("Product", foreign_keys=[component_id])
    operation = relationship("RoutingOperation")

class Routing(Base):
    """Routing - manufacturing process steps"""
    __tablename__ = "routings"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    routing_code = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Product
    product_id = Column(String, ForeignKey("products.id"))
    
    is_active = Column(Boolean, default=True)
    
    # Total Times (calculated from operations)
    total_setup_time = Column(Float, default=0.0)  # minutes
    total_run_time = Column(Float, default=0.0)  # minutes per unit
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    operations = relationship("RoutingOperation", back_populates="routing", cascade="all, delete-orphan")

class RoutingOperation(Base):
    """Routing Operation - individual step in manufacturing process"""
    __tablename__ = "routing_operations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    routing_id = Column(String, ForeignKey("routings.id"), nullable=False)
    
    operation_number = Column(Integer, nullable=False)
    operation_name = Column(String, nullable=False)
    description = Column(Text)
    
    # Work Center / Department
    work_center_code = Column(String)
    department_id = Column(String, ForeignKey("departments.id"))
    
    # Timing
    setup_time = Column(Float, default=0.0)  # minutes
    run_time_per_unit = Column(Float, default=0.0)  # minutes per unit
    
    # Costing
    hourly_rate = Column(Float, default=0.0)
    overhead_rate = Column(Float, default=0.0)  # % of labor or fixed amount
    
    # Quality Control
    requires_qc = Column(Boolean, default=False)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    routing = relationship("Routing", back_populates="operations")
    department = relationship("Department")

class ProductionOrder(Base):
    """Production Order - manufacturing job"""
    __tablename__ = "production_orders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id"))
    
    po_number = Column(String, nullable=False, unique=True, index=True)
    order_date = Column(Date, nullable=False)
    scheduled_start = Column(DateTime)
    scheduled_end = Column(DateTime)
    actual_start = Column(DateTime)
    actual_end = Column(DateTime)
    
    # Product
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    bom_id = Column(String, ForeignKey("bill_of_materials.id"))
    routing_id = Column(String, ForeignKey("routings.id"))
    
    # Quantities
    planned_quantity = Column(Float, nullable=False)
    produced_quantity = Column(Float, default=0.0)
    scrapped_quantity = Column(Float, default=0.0)
    
    # Warehouses
    source_warehouse_id = Column(String, ForeignKey("warehouses.id"))  # Raw materials
    destination_warehouse_id = Column(String, ForeignKey("warehouses.id"))  # Finished goods
    
    # Status
    status = Column(String, default="draft")  # draft, confirmed, in_progress, completed, cancelled
    
    # Costing
    material_cost = Column(Float, default=0.0)
    labor_cost = Column(Float, default=0.0)
    overhead_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)
    
    # Reference
    sales_order_id = Column(String, ForeignKey("sales_orders.id"))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    bom = relationship("BillOfMaterials")
    routing = relationship("Routing")
    department = relationship("Department")
    source_warehouse = relationship("Warehouse", foreign_keys=[source_warehouse_id])
    destination_warehouse = relationship("Warehouse", foreign_keys=[destination_warehouse_id])
    sales_order = relationship("SalesOrder")
    lines = relationship("ProductionOrderLine", back_populates="production_order", cascade="all, delete-orphan")
    wip_entries = relationship("WorkInProgress", back_populates="production_order", cascade="all, delete-orphan")

class ProductionOrderLine(Base):
    """Production Order Line - materials consumed"""
    __tablename__ = "production_order_lines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    production_order_id = Column(String, ForeignKey("production_orders.id"), nullable=False)
    
    line_type = Column(String, nullable=False)  # material, labor, overhead
    line_number = Column(Integer, nullable=False)
    
    # Material
    product_id = Column(String, ForeignKey("products.id"))
    planned_quantity = Column(Float, default=0.0)
    consumed_quantity = Column(Float, default=0.0)
    unit_of_measure = Column(String)
    
    # Costing
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Operation
    operation_id = Column(String, ForeignKey("routing_operations.id"))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    production_order = relationship("ProductionOrder", back_populates="lines")
    product = relationship("Product")
    operation = relationship("RoutingOperation")

class WorkInProgress(Base):
    """WIP Tracking - work in progress inventory"""
    __tablename__ = "work_in_progress"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    production_order_id = Column(String, ForeignKey("production_orders.id"), nullable=False)
    
    transaction_date = Column(DateTime, default=datetime.utcnow)
    transaction_type = Column(String, nullable=False)  # material_issue, labor, overhead, completion
    
    # Amounts
    material_cost = Column(Float, default=0.0)
    labor_cost = Column(Float, default=0.0)
    overhead_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Quantities
    quantity = Column(Float, default=0.0)
    
    # GL Posting
    journal_entry_id = Column(String, ForeignKey("journal_entries.id"))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    production_order = relationship("ProductionOrder", back_populates="wip_entries")
    journal_entry = relationship("JournalEntry")

class CostLayer(Base):
    """Cost Layer - inventory costing (FIFO/LIFO/Average)"""
    __tablename__ = "cost_layers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(String, ForeignKey("warehouses.id"))
    
    # Layer Info
    layer_date = Column(DateTime, default=datetime.utcnow)
    transaction_type = Column(String, nullable=False)  # purchase, production, adjustment, sale
    reference_id = Column(String)  # PO, Production Order, etc
    
    # Quantities
    quantity_in = Column(Float, default=0.0)
    quantity_out = Column(Float, default=0.0)
    quantity_remaining = Column(Float, default=0.0)
    
    # Costing
    unit_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    
    # Batch/Serial
    batch_lot_id = Column(String, ForeignKey("batch_lots.id"))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    warehouse = relationship("Warehouse")

# ============================================================================
# PHASE 2: ADVANCED INVENTORY
# ============================================================================

class BatchLot(Base):
    """Batch/Lot Tracking"""
    __tablename__ = "batch_lots"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    batch_number = Column(String, nullable=False, unique=True, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    
    # Dates
    production_date = Column(Date)
    expiry_date = Column(Date)
    received_date = Column(Date)
    
    # Quantities
    initial_quantity = Column(Float, nullable=False)
    available_quantity = Column(Float, nullable=False)
    
    # Source
    supplier_id = Column(String, ForeignKey("suppliers.id"))
    production_order_id = Column(String, ForeignKey("production_orders.id"))
    
    # Quality
    quality_status = Column(String, default="approved")  # approved, hold, rejected
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    supplier = relationship("Supplier")
    production_order = relationship("ProductionOrder")

class SerialNumber(Base):
    """Serial Number Tracking"""
    __tablename__ = "serial_numbers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    serial_number = Column(String, nullable=False, unique=True, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    batch_lot_id = Column(String, ForeignKey("batch_lots.id"))
    
    # Location
    warehouse_id = Column(String, ForeignKey("warehouses.id"))
    current_location = Column(String)
    
    # Status
    status = Column(String, default="in_stock")  # in_stock, sold, scrapped, in_transit
    
    # Dates
    manufactured_date = Column(Date)
    warranty_expiry = Column(Date)
    
    # Ownership
    customer_id = Column(String, ForeignKey("customers.id"))  # If sold
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    batch_lot = relationship("BatchLot")
    warehouse = relationship("Warehouse")
    customer = relationship("Customer")

class QualityControl(Base):
    """Quality Control Inspections"""
    __tablename__ = "quality_controls"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    qc_number = Column(String, nullable=False, unique=True, index=True)
    inspection_date = Column(Date, nullable=False)
    
    # What is being inspected
    inspection_type = Column(String, nullable=False)  # incoming, in_process, final, audit
    product_id = Column(String, ForeignKey("products.id"))
    batch_lot_id = Column(String, ForeignKey("batch_lots.id"))
    production_order_id = Column(String, ForeignKey("production_orders.id"))
    
    # Results
    quantity_inspected = Column(Float, nullable=False)
    quantity_passed = Column(Float, default=0.0)
    quantity_failed = Column(Float, default=0.0)
    
    # Decision
    decision = Column(String, nullable=False)  # approved, rejected, conditional, hold
    
    # Inspector
    inspector_id = Column(String, ForeignKey("users.id"))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    batch_lot = relationship("BatchLot")
    production_order = relationship("ProductionOrder")
    inspector = relationship("User")

class ConsignmentStock(Base):
    """Consignment Inventory (goods held for/by third parties)"""
    __tablename__ = "consignment_stocks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    consignment_type = Column(String, nullable=False)  # consignment_in, consignment_out
    
    # Product
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    
    # Third Party
    customer_id = Column(String, ForeignKey("customers.id"))  # For consignment_out
    supplier_id = Column(String, ForeignKey("suppliers.id"))  # For consignment_in
    
    # Location
    warehouse_id = Column(String, ForeignKey("warehouses.id"))
    
    # Dates
    consignment_date = Column(Date, nullable=False)
    expected_return_date = Column(Date)
    actual_return_date = Column(Date)
    
    # Status
    status = Column(String, default="active")  # active, returned, sold
    
    # Costing (for insurance purposes)
    unit_value = Column(Float, default=0.0)
    total_value = Column(Float, default=0.0)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    product = relationship("Product")
    customer = relationship("Customer")
    supplier = relationship("Supplier")
    warehouse = relationship("Warehouse")

class LandedCost(Base):
    """Landed Cost Components (duties, shipping, insurance)"""
    __tablename__ = "landed_costs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    landed_cost_number = Column(String, nullable=False, unique=True, index=True)
    reference_date = Column(Date, nullable=False)
    
    # Source Document
    reference_type = Column(String, nullable=False)  # purchase_order, goods_receipt
    reference_id = Column(String, nullable=False)
    
    # Cost Components
    freight_cost = Column(Float, default=0.0)
    insurance_cost = Column(Float, default=0.0)
    customs_duty = Column(Float, default=0.0)
    handling_charges = Column(Float, default=0.0)
    other_charges = Column(Float, default=0.0)
    total_landed_cost = Column(Float, default=0.0)
    
    # Allocation Method
    allocation_method = Column(String, default="value")  # value, quantity, weight, volume
    
    # Status
    status = Column(String, default="draft")  # draft, posted
    posted_at = Column(DateTime)
    
    # GL Posting
    journal_entry_id = Column(String, ForeignKey("journal_entries.id"))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    journal_entry = relationship("JournalEntry")
    allocations = relationship("LandedCostAllocation", back_populates="landed_cost", cascade="all, delete-orphan")

class LandedCostAllocation(Base):
    """Landed Cost Allocation to Products"""
    __tablename__ = "landed_cost_allocations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    landed_cost_id = Column(String, ForeignKey("landed_costs.id"), nullable=False)
    
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    
    # Base Values (for allocation calculation)
    base_value = Column(Float, nullable=False)  # Product value
    base_quantity = Column(Float)  # For quantity-based allocation
    base_weight = Column(Float)  # For weight-based allocation
    base_volume = Column(Float)  # For volume-based allocation
    
    # Allocated Costs
    allocated_freight = Column(Float, default=0.0)
    allocated_insurance = Column(Float, default=0.0)
    allocated_duty = Column(Float, default=0.0)
    allocated_handling = Column(Float, default=0.0)
    allocated_other = Column(Float, default=0.0)
    total_allocated = Column(Float, default=0.0)
    
    # Unit Cost Adjustment
    original_unit_cost = Column(Float, nullable=False)
    adjusted_unit_cost = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    landed_cost = relationship("LandedCost", back_populates="allocations")
    product = relationship("Product")

class TransferPricingRule(Base):
    """Transfer Pricing Rules (inter-branch/department pricing)"""
    __tablename__ = "transfer_pricing_rules"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    rule_name = Column(String, nullable=False)
    
    # Product/Category
    product_id = Column(String, ForeignKey("products.id"))
    product_category = Column(String)  # Apply to category
    
    # Locations
    from_location_type = Column(String)  # warehouse, department, branch
    from_location_id = Column(String)
    to_location_type = Column(String)
    to_location_id = Column(String)
    
    # Pricing Method
    pricing_method = Column(String, nullable=False)  # cost, cost_plus, market_price, negotiated
    
    # Cost Plus
    markup_percentage = Column(Float, default=0.0)
    fixed_markup = Column(Float, default=0.0)
    
    # Fixed Price
    transfer_price = Column(Float)
    
    is_active = Column(Boolean, default=True)
    effective_from = Column(Date)
    effective_to = Column(Date)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    product = relationship("Product")

# ============================================================================
# PHASE 2: ORGANIZATIONAL HIERARCHY (for consolidation)
# ============================================================================

class Sector(Base):
    """Sector - middle level: Department → Sector → Enterprise"""
    __tablename__ = "sectors"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    sector_code = Column(String, nullable=False, unique=True, index=True)
    sector_name = Column(String, nullable=False)
    description = Column(Text)
    
    # Hierarchy
    enterprise_id = Column(String, ForeignKey("enterprises.id"))
    
    # Manager
    manager_id = Column(String, ForeignKey("users.id"))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    enterprise = relationship("Enterprise", back_populates="sectors")
    manager = relationship("User")

class Enterprise(Base):
    """Enterprise - top level for multi-company consolidation"""
    __tablename__ = "enterprises"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    
    enterprise_code = Column(String, nullable=False, unique=True, index=True)
    enterprise_name = Column(String, nullable=False)
    description = Column(Text)
    
    # Consolidation Settings
    consolidation_currency = Column(String, default="ZMW")
    elimination_method = Column(String, default="full")  # full, proportional
    
    # CEO/Head
    ceo_id = Column(String, ForeignKey("users.id"))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ceo = relationship("User")
    sectors = relationship("Sector", back_populates="enterprise", cascade="all, delete-orphan")

# ============================================================================
# PHASE 3: STATUTORY COMPLIANCE & NOTIFICATIONS
# ============================================================================

class StatutoryObligation(Base):
    """Statutory compliance tracking (PAYE, NAPSA, NHIMA, VAT, etc.)"""
    __tablename__ = "statutory_obligations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Obligation Details
    obligation_type = Column(String, nullable=False, index=True)  # PAYE, NAPSA, NHIMA, VAT, WHT, etc.
    obligation_name = Column(String, nullable=False)
    description = Column(Text)
    
    # Frequency & Timing
    frequency = Column(String, nullable=False)  # monthly, quarterly, annual
    due_day_of_month = Column(Integer)  # e.g., 10 for PAYE/NAPSA/NHIMA
    due_month = Column(Integer)  # For annual/quarterly
    
    # Amounts & Status
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    amount_due = Column(Float, default=0.0)
    amount_paid = Column(Float, default=0.0)
    
    status = Column(String, default="pending", index=True)  # pending, paid, overdue, exempted
    compliance_status = Column(String, default="not_started")  # not_started, in_progress, completed
    
    # Confirmation
    confirmed_by_user = Column(Boolean, default=False)
    confirmed_at = Column(DateTime)
    confirmed_by = Column(String, ForeignKey("users.id"))
    
    # Payments
    payment_reference = Column(String)
    payment_date = Column(Date)
    payment_method = Column(String)
    
    # Alerts
    alert_days_before = Column(Integer, default=5)  # Alert 5 days before due date
    last_alert_sent = Column(DateTime)
    
    # Additional Data
    extra_data = Column(JSON)  # Store additional obligation-specific data (renamed from 'metadata' to avoid SQLAlchemy conflict)
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company")
    confirmer = relationship("User", foreign_keys=[confirmed_by])

class ComplianceChecklist(Base):
    """Checklist items for compliance tracking"""
    __tablename__ = "compliance_checklists"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    obligation_id = Column(String, ForeignKey("statutory_obligations.id"), index=True)
    
    # Checklist Item
    item_name = Column(String, nullable=False)
    item_description = Column(Text)
    item_category = Column(String)  # preparation, calculation, filing, payment, documentation
    
    # Status
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    completed_by = Column(String, ForeignKey("users.id"))
    
    # Order & Priority
    sequence_order = Column(Integer, default=0)
    is_required = Column(Boolean, default=True)
    
    # Attachments
    attachment_required = Column(Boolean, default=False)
    attachment_path = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    obligation = relationship("StatutoryObligation")
    completer = relationship("User", foreign_keys=[completed_by])

# ============================================================================
# PHASE 3: ENHANCED HR/PAYROLL MODELS
# ============================================================================

class EmployeeContract(Base):
    """Employment contracts with document storage"""
    __tablename__ = "employee_contracts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False, index=True)
    
    # Contract Details
    contract_type = Column(String, nullable=False)  # permanent, fixed_term, contract, probation
    contract_number = Column(String)
    
    # Dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)  # Null for permanent
    probation_end_date = Column(Date)
    
    # Compensation
    salary_amount = Column(Float, nullable=False)
    salary_currency = Column(String, default="ZMW")
    salary_frequency = Column(String, default="monthly")  # monthly, weekly, daily
    
    # Terms
    position_title = Column(String)
    department_id = Column(String, ForeignKey("departments.id"))
    reporting_to = Column(String, ForeignKey("employees.id"))
    work_location = Column(String)
    
    # Benefits
    benefits_package = Column(JSON)  # housing, transport, medical, etc.
    leave_days_annual = Column(Integer, default=24)
    
    # Documents
    contract_template_id = Column(String)
    signed_contract_path = Column(String)
    signed_date = Column(Date)
    
    # Status
    status = Column(String, default="draft")  # draft, active, expired, terminated
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id])
    department = relationship("Department")
    supervisor = relationship("Employee", foreign_keys=[reporting_to])

class SalaryComponentDefinition(Base):
    """Configurable salary components (earnings & deductions)"""
    __tablename__ = "salary_component_definitions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Component Details
    component_code = Column(String, nullable=False, index=True)
    component_name = Column(String, nullable=False)
    component_type = Column(String, nullable=False)  # earning, deduction
    component_category = Column(String)  # basic, allowance, overtime, statutory, loan, benefit
    
    # Calculation
    calculation_method = Column(String, default="fixed")  # fixed, percentage, formula
    calculation_formula = Column(Text)  # Formula or percentage
    base_component = Column(String)  # Which component to calculate from (e.g., "basic_salary")
    
    # Tax Treatment
    is_taxable = Column(Boolean, default=True)
    is_pensionable = Column(Boolean, default=True)  # Included in NAPSA calculation
    
    # Statutory
    is_statutory = Column(Boolean, default=False)  # PAYE, NAPSA, NHIMA
    statutory_type = Column(String)  # paye, napsa_employee, napsa_employer, nhima_employee, nhima_employer
    
    # Account Mapping
    gl_account_id = Column(String, ForeignKey("accounts.id"))  # Link to chart of accounts
    
    # Status
    is_active = Column(Boolean, default=True)
    effective_from = Column(Date)
    effective_to = Column(Date)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    gl_account = relationship("Account")

class Payrun(Base):
    """Payroll run/batch processing"""
    __tablename__ = "payruns"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Payrun Details
    payrun_number = Column(String, nullable=False, unique=True, index=True)
    payrun_name = Column(String)
    
    # Period
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False)
    payment_date = Column(Date, nullable=False)
    
    # Currency
    currency = Column(String, default="ZMW")
    exchange_rate = Column(Float, default=1.0)
    
    # Totals
    total_gross = Column(Float, default=0.0)
    total_deductions = Column(Float, default=0.0)
    total_net = Column(Float, default=0.0)
    total_employer_cost = Column(Float, default=0.0)
    
    # Statutory Totals
    total_paye = Column(Float, default=0.0)
    total_napsa_employee = Column(Float, default=0.0)
    total_napsa_employer = Column(Float, default=0.0)
    total_nhima_employee = Column(Float, default=0.0)
    total_nhima_employer = Column(Float, default=0.0)
    
    # Status
    status = Column(String, default="draft", index=True)  # draft, validated, posted, exported, archived
    
    # Validation
    validation_errors = Column(JSON)  # List of validation issues
    validated_at = Column(DateTime)
    validated_by = Column(String, ForeignKey("users.id"))
    
    # Posting
    posted_to_gl = Column(Boolean, default=False)
    gl_journal_id = Column(String, ForeignKey("journal_entries.id"))
    posted_at = Column(DateTime)
    posted_by = Column(String, ForeignKey("users.id"))
    
    # Export
    bank_file_path = Column(String)
    exported_at = Column(DateTime)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    company = relationship("Company")
    gl_journal = relationship("JournalEntry")
    payslips = relationship("Payslip", back_populates="payrun", cascade="all, delete-orphan")

class Payslip(Base):
    """Individual employee payslip"""
    __tablename__ = "payslips"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    payrun_id = Column(String, ForeignKey("payruns.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False, index=True)
    
    # Employee Snapshot (cached at time of payrun)
    employee_name = Column(String)
    employee_number = Column(String)
    department_name = Column(String)
    position = Column(String)
    
    # Earnings
    basic_salary = Column(Float, default=0.0)
    earnings_json = Column(JSON)  # All earnings components
    total_earnings = Column(Float, default=0.0)
    
    # Deductions
    deductions_json = Column(JSON)  # All deduction components
    total_deductions = Column(Float, default=0.0)
    
    # Statutory
    paye_amount = Column(Float, default=0.0)
    napsa_employee = Column(Float, default=0.0)
    napsa_employer = Column(Float, default=0.0)
    nhima_employee = Column(Float, default=0.0)
    nhima_employer = Column(Float, default=0.0)
    
    # Totals
    gross_pay = Column(Float, default=0.0)
    taxable_income = Column(Float, default=0.0)
    net_pay = Column(Float, default=0.0)
    employer_cost = Column(Float, default=0.0)
    
    # Payment
    payment_method = Column(String, default="bank_transfer")  # bank_transfer, cash, mobile_money
    bank_account_number = Column(String)
    bank_name = Column(String)
    mobile_money_number = Column(String)
    
    # Documents
    payslip_pdf_path = Column(String)
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)
    
    # Status
    status = Column(String, default="draft")  # draft, approved, paid
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    payrun = relationship("Payrun", back_populates="payslips")
    employee = relationship("Employee")

class EmployeeLoan(Base):
    """Employee loans and salary advances"""
    __tablename__ = "employee_loans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False, index=True)
    
    # Loan Details
    loan_number = Column(String, nullable=False, unique=True, index=True)
    loan_type = Column(String, nullable=False)  # salary_advance, emergency_loan, housing_loan, etc.
    loan_purpose = Column(Text)
    
    # Amounts
    principal_amount = Column(Float, nullable=False)
    interest_rate = Column(Float, default=0.0)  # Annual percentage
    total_amount = Column(Float, nullable=False)  # Principal + Interest
    outstanding_balance = Column(Float, nullable=False)
    
    # Repayment
    repayment_amount = Column(Float, nullable=False)  # Monthly deduction
    repayment_start_date = Column(Date, nullable=False)
    repayment_months = Column(Integer, nullable=False)
    remaining_months = Column(Integer)
    
    # Amortization
    amortization_schedule = Column(JSON)  # Monthly breakdown
    
    # Approval
    requested_date = Column(Date, default=datetime.utcnow)
    approved_by = Column(String, ForeignKey("users.id"))
    approved_date = Column(Date)
    approval_notes = Column(Text)
    
    # Disbursement
    disbursed_date = Column(Date)
    disbursement_method = Column(String)  # bank_transfer, cash, offset_against_salary
    disbursement_reference = Column(String)
    
    # Status
    status = Column(String, default="pending", index=True)  # pending, approved, rejected, disbursed, active, completed, written_off
    
    # GL Integration
    gl_journal_id = Column(String, ForeignKey("journal_entries.id"))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    employee = relationship("Employee")
    approver = relationship("User", foreign_keys=[approved_by])
    gl_journal = relationship("JournalEntry")

class JobRequisition(Base):
    """Job requisition and approval workflow"""
    __tablename__ = "job_requisitions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Requisition Details
    requisition_number = Column(String, nullable=False, unique=True, index=True)
    position_title = Column(String, nullable=False)
    department_id = Column(String, ForeignKey("departments.id"), nullable=False)
    
    # Position Details
    job_description = Column(Text)
    required_qualifications = Column(Text)
    experience_years = Column(Integer)
    number_of_positions = Column(Integer, default=1)
    
    # Compensation
    salary_band_min = Column(Float)
    salary_band_max = Column(Float)
    employment_type = Column(String)  # permanent, contract, part_time
    
    # Budget
    budget_allocated = Column(Float)
    cost_center_code = Column(String)
    
    # Timing
    requested_start_date = Column(Date)
    urgency = Column(String, default="normal")  # low, normal, high, urgent
    
    # Approval Workflow
    approval_status = Column(String, default="pending", index=True)  # pending, approved, rejected
    approval_chain = Column(JSON)  # List of approvers
    current_approver_id = Column(String, ForeignKey("users.id"))
    
    # Status
    status = Column(String, default="draft")  # draft, submitted, approved, rejected, filled, cancelled
    filled_date = Column(Date)
    
    # Justification
    business_justification = Column(Text)
    replacement_for = Column(String, ForeignKey("employees.id"))  # If replacing someone
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    department = relationship("Department")
    current_approver = relationship("User", foreign_keys=[current_approver_id])
    replacement_employee = relationship("Employee")

# ============================================================================
# PHASE 3: ENHANCED FINANCE MODELS
# ============================================================================

class TaxSetting(Base):
    """Tax configuration (PAYE, VAT, WHT, etc.)"""
    __tablename__ = "tax_settings"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Tax Type
    tax_type = Column(String, nullable=False, index=True)  # PAYE, VAT, WHT, Turnover, Excise
    tax_name = Column(String, nullable=False)
    
    # Tax Configuration
    tax_jurisdiction = Column(String, default="Zambia")
    tax_rate = Column(Float)  # Flat rate if applicable
    tax_brackets = Column(JSON)  # For progressive taxes like PAYE
    
    # GL Account Mapping
    tax_payable_account_id = Column(String, ForeignKey("accounts.id"))
    tax_expense_account_id = Column(String, ForeignKey("accounts.id"))
    
    # Effective Dates
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    
    # Filing Details
    filing_frequency = Column(String)  # monthly, quarterly, annual
    filing_due_day = Column(Integer)  # Day of month due
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tax_payable_account = relationship("Account", foreign_keys=[tax_payable_account_id])
    tax_expense_account = relationship("Account", foreign_keys=[tax_expense_account_id])


# ============================================================================
# PHASE 4: SUPER ADMIN & TENANT MANAGEMENT
# ============================================================================

class SubscriptionPlan(Base):
    """Subscription plans for multi-tenant SaaS (Free, Basic, Premium, Enterprise)"""
    __tablename__ = "subscription_plans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    plan_code = Column(String, nullable=False, unique=True, index=True)
    plan_name = Column(String, nullable=False)
    description = Column(Text)
    
    # Pricing
    price_monthly = Column(Float, nullable=False, default=0.0)
    price_annual = Column(Float, nullable=False, default=0.0)
    currency = Column(String, default="ZMW")
    
    # Limits
    max_users = Column(Integer, default=5)
    max_employees = Column(Integer, default=50)
    max_storage_gb = Column(Integer, default=10)
    max_api_calls_per_month = Column(Integer, default=10000)
    max_branches = Column(Integer, default=1)
    
    # Module Access
    modules_included = Column(JSON)  # ["finance", "hr", "inventory", "sales"]
    features_included = Column(JSON)  # ["multi_currency", "reporting", "mobile_app"]
    
    # Settings
    trial_days = Column(Integer, default=7)
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlatformSettings(Base):
    """Global platform-wide settings managed by Super Admin"""
    __tablename__ = "platform_settings"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    setting_key = Column(String, nullable=False, unique=True, index=True)
    setting_value = Column(JSON)
    setting_type = Column(String, nullable=False)  # string, number, boolean, json
    setting_category = Column(String, index=True)  # security, notifications, ai, billing
    description = Column(Text)
    is_sensitive = Column(Boolean, default=False)
    updated_by = Column(String, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SupportTicket(Base):
    """Customer support tickets from tenants"""
    __tablename__ = "support_tickets"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    ticket_number = Column(String, nullable=False, unique=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Requester
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    requester_email = Column(String)
    requester_phone = Column(String)
    
    # Ticket Details
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, index=True)  # technical, billing, feature_request, bug
    priority = Column(String, default="medium", index=True)  # low, medium, high, critical
    status = Column(String, default="open", index=True)  # open, in_progress, waiting_customer, resolved, closed
    
    # Assignment
    assigned_to = Column(String, ForeignKey("users.id"))
    assigned_at = Column(DateTime)
    
    # Resolution
    resolution = Column(Text)
    resolved_at = Column(DateTime)
    resolved_by = Column(String, ForeignKey("users.id"))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_response_at = Column(DateTime)
    
    # Relationships
    company = relationship("Company")
    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])
    resolver = relationship("User", foreign_keys=[resolved_by])


class SystemLog(Base):
    """Platform-wide system logs for monitoring and debugging"""
    __tablename__ = "system_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    
    # Log Details
    log_level = Column(String, nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_category = Column(String, index=True)  # api, database, auth, billing, integration
    message = Column(Text, nullable=False)
    stack_trace = Column(Text)
    
    # Request Context
    endpoint = Column(String, index=True)
    http_method = Column(String)
    status_code = Column(Integer, index=True)
    response_time_ms = Column(Integer)
    ip_address = Column(String, index=True)
    user_agent = Column(Text)
    
    # Additional Data
    extra_data = Column(JSON)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)


class APIUsageLog(Base):
    """Track API usage per tenant for billing and analytics"""
    __tablename__ = "api_usage_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    
    # API Call Details
    endpoint = Column(String, nullable=False, index=True)
    http_method = Column(String, nullable=False)
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    
    # Usage Metrics
    request_size_bytes = Column(Integer)
    response_size_bytes = Column(Integer)
    
    # Billing
    is_billable = Column(Boolean, default=True, index=True)
    cost_credits = Column(Float, default=1.0)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    
    # Aggregation (for monthly billing)
    year_month = Column(String, index=True)  # Format: "2025-11"
    
    # Relationships
    company = relationship("Company")


class TenantModule(Base):
    """Module access control per tenant"""
    __tablename__ = "tenant_modules"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Module Details
    module_code = Column(String, nullable=False, index=True)  # finance, hr, inventory, sales, etc.
    module_name = Column(String, nullable=False)
    is_enabled = Column(Boolean, default=True, index=True)
    
    # Access Control
    enabled_at = Column(DateTime)
    enabled_by = Column(String, ForeignKey("users.id"))
    disabled_at = Column(DateTime)
    disabled_by = Column(String, ForeignKey("users.id"))
    
    # Usage Tracking
    last_accessed_at = Column(DateTime)
    access_count = Column(Integer, default=0)
    
    # Relationships
    company = relationship("Company")


class SubscriptionPayment(Base):
    """Payment transactions for subscription billing"""
    __tablename__ = "subscription_payments"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Transaction Details
    transaction_number = Column(String, nullable=False, unique=True, index=True)
    transaction_type = Column(String, nullable=False, index=True)  # subscription, upgrade, addon, refund
    
    # Amount
    amount = Column(Float, nullable=False)
    currency = Column(String, default="ZMW")
    
    # Payment Method
    payment_method = Column(String, nullable=False, index=True)  # mtn_money, airtel_money, bank_transfer, stripe
    payment_reference = Column(String, index=True)
    
    # Status
    status = Column(String, default="pending", index=True)  # pending, processing, completed, failed, refunded
    
    # Payment Provider Response
    provider_response = Column(JSON)
    provider_transaction_id = Column(String, index=True)
    
    # Subscription Context
    subscription_plan_id = Column(String, ForeignKey("subscription_plans.id"))
    billing_period_start = Column(Date)
    billing_period_end = Column(Date)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    
    # Relationships
    company = relationship("Company")
    subscription_plan = relationship("SubscriptionPlan")

# ============================================================================
# ADDON MARKETPLACE MODELS
# ============================================================================


# ============================================================================
# ADDON MARKETPLACE MODELS
# ============================================================================

class Addon(Base):
    __tablename__ = "addons"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    addon_code = Column(String, unique=True, nullable=False)
    addon_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text)
    icon = Column(String)
    is_official = Column(Boolean, default=True)
    pricing_model = Column(String)
    monthly_price = Column(Float, default=0.0)
    features = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class CompanyAddon(Base):
    __tablename__ = "company_addons"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    addon_id = Column(String, ForeignKey('addons.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    activated_at = Column(DateTime, default=datetime.utcnow)
    deactivated_at = Column(DateTime, nullable=True)
    settings = Column(Text)

# Construction & Real Estate
class ConstructionProject(Base):
    __tablename__ = "construction_projects"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    project_code = Column(String, nullable=False)
    project_name = Column(String, nullable=False)
    client_name = Column(String)
    location = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    budget = Column(Float)
    actual_cost = Column(Float, default=0.0)
    status = Column(String, default='planning')
    progress_percent = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class BillOfQuantities(Base):
    __tablename__ = "bill_of_quantities"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    project_id = Column(String, ForeignKey('construction_projects.id'))
    item_code = Column(String)
    description = Column(Text)
    unit = Column(String)
    quantity = Column(Float)
    rate = Column(Float)
    amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

# Agriculture & Agribusiness
class Farm(Base):
    __tablename__ = "farms"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    farm_code = Column(String, nullable=False)
    farm_name = Column(String, nullable=False)
    location = Column(String)
    total_area = Column(Float)
    area_unit = Column(String, default='hectares')
    farm_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class CropPlanting(Base):
    __tablename__ = "crop_plantings"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    farm_id = Column(String, ForeignKey('farms.id'))
    crop_name = Column(String, nullable=False)
    variety = Column(String)
    planting_date = Column(Date)
    expected_harvest = Column(Date)
    area_planted = Column(Float)
    expected_yield = Column(Float)
    actual_yield = Column(Float)
    status = Column(String, default='planted')
    created_at = Column(DateTime, default=datetime.utcnow)

class Livestock(Base):
    __tablename__ = "livestock"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    farm_id = Column(String, ForeignKey('farms.id'))
    animal_type = Column(String, nullable=False)
    tag_number = Column(String, unique=True)
    breed = Column(String)
    date_of_birth = Column(Date)
    gender = Column(String)
    weight = Column(Float)
    health_status = Column(String, default='healthy')
    created_at = Column(DateTime, default=datetime.utcnow)

# Healthcare & Pharmaceuticals
class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    patient_number = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(Date)
    gender = Column(String)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)
    blood_group = Column(String)
    allergies = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    patient_id = Column(String, ForeignKey('patients.id'))
    doctor_name = Column(String)
    appointment_date = Column(DateTime)
    reason = Column(Text)
    status = Column(String, default='scheduled')
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Education
class Student(Base):
    __tablename__ = "students"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    student_number = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(Date)
    gender = Column(String)
    grade_level = Column(String)
    enrollment_date = Column(Date)
    guardian_name = Column(String)
    guardian_phone = Column(String)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

# Transport & Logistics
class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    registration_number = Column(String, unique=True, nullable=False)
    vehicle_type = Column(String)
    make = Column(String)
    model = Column(String)
    year = Column(Integer)
    capacity = Column(Float)
    fuel_type = Column(String)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

class Trip(Base):
    __tablename__ = "trips"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    vehicle_id = Column(String, ForeignKey('vehicles.id'))
    trip_number = Column(String, nullable=False)
    driver_name = Column(String)
    origin = Column(String)
    destination = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    distance_km = Column(Float)
    freight_charges = Column(Float)
    status = Column(String, default='scheduled')
    created_at = Column(DateTime, default=datetime.utcnow)

# Hospitality
class Room(Base):
    __tablename__ = "hotel_rooms"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    room_number = Column(String, nullable=False)
    room_type = Column(String)
    capacity = Column(Integer)
    rate_per_night = Column(Float)
    floor = Column(Integer)
    status = Column(String, default='available')
    created_at = Column(DateTime, default=datetime.utcnow)

class Reservation(Base):
    __tablename__ = "reservations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    room_id = Column(String, ForeignKey('hotel_rooms.id'))
    guest_name = Column(String, nullable=False)
    guest_phone = Column(String)
    check_in = Column(DateTime)
    check_out = Column(DateTime)
    total_amount = Column(Float)
    status = Column(String, default='confirmed')
    created_at = Column(DateTime, default=datetime.utcnow)

# Retail Store Management
class Store(Base):
    __tablename__ = "retail_stores"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    store_code = Column(String, nullable=False)
    store_name = Column(String, nullable=False)
    location = Column(String)
    phone = Column(String)
    manager_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Real Estate Development
class RealEstateProperty(Base):
    __tablename__ = "real_estate_properties"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    property_code = Column(String, nullable=False)
    property_name = Column(String, nullable=False)
    property_type = Column(String)
    address = Column(Text)
    size_sqm = Column(Float)
    purchase_price = Column(Float)
    current_value = Column(Float)
    status = Column(String, default='available')
    created_at = Column(DateTime, default=datetime.utcnow)

class Lease(Base):
    __tablename__ = "leases"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    property_id = Column(String, ForeignKey('real_estate_properties.id'))
    tenant_name = Column(String, nullable=False)
    lease_start = Column(Date)
    lease_end = Column(Date)
    monthly_rent = Column(Float)
    deposit_amount = Column(Float)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

# Legal Practice Management
class LegalCase(Base):
    __tablename__ = "legal_cases"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    case_number = Column(String, unique=True, nullable=False)
    case_title = Column(String, nullable=False)
    client_name = Column(String)
    case_type = Column(String)
    filing_date = Column(Date)
    court_name = Column(String)
    status = Column(String, default='open')
    created_at = Column(DateTime, default=datetime.utcnow)

class LegalDocument(Base):
    __tablename__ = "legal_documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    case_id = Column(String, ForeignKey('legal_cases.id'))
    document_type = Column(String)
    document_title = Column(String, nullable=False)
    file_path = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

# NGO & Non-Profit
class Donor(Base):
    __tablename__ = "donors"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    donor_code = Column(String, nullable=False)
    donor_name = Column(String, nullable=False)
    donor_type = Column(String)
    contact_person = Column(String)
    email = Column(String)
    phone = Column(String)
    total_donations = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Grant(Base):
    __tablename__ = "grants"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    donor_id = Column(String, ForeignKey('donors.id'))
    grant_number = Column(String, nullable=False)
    grant_title = Column(String, nullable=False)
    grant_amount = Column(Float)
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

# Advanced Manufacturing
class AdvProductionOrder(Base):
    __tablename__ = "adv_production_orders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    order_number = Column(String, unique=True, nullable=False)
    product_name = Column(String, nullable=False)
    quantity_ordered = Column(Float)
    quantity_produced = Column(Float, default=0.0)
    start_date = Column(Date)
    target_date = Column(Date)
    status = Column(String, default='planned')
    created_at = Column(DateTime, default=datetime.utcnow)

class AdvQualityControl(Base):
    __tablename__ = "adv_quality_controls"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    production_order_id = Column(String, ForeignKey('adv_production_orders.id'))
    inspection_date = Column(Date)
    inspector_name = Column(String)
    result = Column(String)
    defects_found = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Logistics & Warehousing
class LogisticsWarehouse(Base):
    __tablename__ = "logistics_warehouses"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    warehouse_code = Column(String, nullable=False)
    warehouse_name = Column(String, nullable=False)
    location = Column(String)
    capacity = Column(Float)
    manager_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LogisticsShipment(Base):
    __tablename__ = "logistics_shipments"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    shipment_number = Column(String, unique=True, nullable=False)
    origin = Column(String)
    destination = Column(String)
    carrier = Column(String)
    tracking_number = Column(String)
    ship_date = Column(Date)
    estimated_arrival = Column(Date)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)

# Telecommunications
class Subscriber(Base):
    __tablename__ = "subscribers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    subscriber_number = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String)
    email = Column(String)
    plan_id = Column(String)
    activation_date = Column(Date)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

class TelecomPlan(Base):
    __tablename__ = "telecom_plans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    plan_code = Column(String, nullable=False)
    plan_name = Column(String, nullable=False)
    monthly_fee = Column(Float)
    data_limit_gb = Column(Float)
    voice_minutes = Column(Integer)
    sms_count = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Energy & Utilities
class Meter(Base):
    __tablename__ = "meters"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    meter_number = Column(String, unique=True, nullable=False)
    meter_type = Column(String)
    customer_name = Column(String)
    location = Column(String)
    installation_date = Column(Date)
    last_reading = Column(Float, default=0.0)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

class Consumption(Base):
    __tablename__ = "consumptions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    meter_id = Column(String, ForeignKey('meters.id'))
    reading_date = Column(Date)
    reading_value = Column(Float)
    consumption_amount = Column(Float)
    billing_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

# Media & Publishing
class MediaContent(Base):
    __tablename__ = "media_contents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    content_code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content_type = Column(String)
    author = Column(String)
    publication_date = Column(Date)
    status = Column(String, default='draft')
    created_at = Column(DateTime, default=datetime.utcnow)

class MediaPublication(Base):
    __tablename__ = "media_publications"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    publication_name = Column(String, nullable=False)
    publisher = Column(String)
    frequency = Column(String)
    subscription_price = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Insurance & Underwriting
class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    policy_number = Column(String, unique=True, nullable=False)
    policyholder_name = Column(String, nullable=False)
    policy_type = Column(String)
    coverage_amount = Column(Float)
    premium_amount = Column(Float)
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

class Claim(Base):
    __tablename__ = "insurance_claims"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    policy_id = Column(String, ForeignKey('insurance_policies.id'))
    claim_number = Column(String, unique=True, nullable=False)
    claim_date = Column(Date)
    claim_amount = Column(Float)
    approved_amount = Column(Float)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)

# Government & Public Sector
class Permit(Base):
    __tablename__ = "permits"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    permit_number = Column(String, unique=True, nullable=False)
    permit_type = Column(String)
    applicant_name = Column(String, nullable=False)
    application_date = Column(Date)
    issue_date = Column(Date)
    expiry_date = Column(Date)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)

class PublicService(Base):
    __tablename__ = "public_services"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    service_code = Column(String, nullable=False)
    service_name = Column(String, nullable=False)
    department = Column(String)
    service_fee = Column(Float)
    processing_time_days = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

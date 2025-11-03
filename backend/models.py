from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Date
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
    role = Column(String, default="user")
    company_id = Column(String, ForeignKey("companies.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    company = relationship("Company", back_populates="users")

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
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    employee_no = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    id_number = Column(String)
    date_of_birth = Column(Date)
    gender = Column(String)
    position = Column(String)
    department_id = Column(String, ForeignKey("departments.id"))
    salary_base = Column(Float, default=0.0)
    bank_account = Column(String)
    tax_id = Column(String)
    date_joined = Column(Date)
    employment_status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="employees")
    department = relationship("Department")

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

class Payslip(Base):
    __tablename__ = "payslips"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    payslip_number = Column(String, nullable=False, unique=True)
    period_month = Column(Integer, nullable=False)
    period_year = Column(Integer, nullable=False)
    basic_salary = Column(Float, nullable=False)
    gross_salary = Column(Float, nullable=False)
    paye_tax = Column(Float, default=0.0)
    napsa_employee = Column(Float, default=0.0)
    napsa_employer = Column(Float, default=0.0)
    nhima_employee = Column(Float, default=0.0)
    nhima_employer = Column(Float, default=0.0)
    total_deductions = Column(Float, default=0.0)
    net_salary = Column(Float, nullable=False)
    status = Column(String, default="draft")
    payment_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    employee = relationship("Employee")

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

class StatutoryObligation(Base):
    __tablename__ = "statutory_obligations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    obligation_type = Column(String, nullable=False)  # PAYE, NAPSA, NHIMA, SDL, VAT, etc.
    description = Column(Text)
    frequency = Column(String, nullable=False)  # monthly, quarterly, annually
    due_day = Column(Integer)  # Day of month when due
    amount = Column(Float)
    status = Column(String, default="pending")  # pending, paid, overdue
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date)
    reference_no = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    period_type = Column(String, default="month")  # month, quarter, year
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    is_closed = Column(Boolean, default=False)
    closed_at = Column(DateTime)
    closed_by = Column(String, ForeignKey("users.id"))
    is_locked = Column(Boolean, default=False)
    locked_at = Column(DateTime)
    locked_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

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

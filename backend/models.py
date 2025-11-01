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
    department = Column(String)
    salary_base = Column(Float, default=0.0)
    bank_account = Column(String)
    tax_id = Column(String)
    date_joined = Column(Date)
    employment_status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="employees")

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    parent_id = Column(String, ForeignKey("accounts.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="accounts")
    parent = relationship("Account", remote_side=[id], backref="children")
    journal_lines = relationship("JournalLine", back_populates="account")

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    journal_number = Column(String, nullable=False, unique=True)
    date = Column(Date, nullable=False)
    description = Column(Text)
    currency = Column(String, default="ZMW")
    total_amount = Column(Float, nullable=False)
    status = Column(String, default="draft")
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="journals")
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

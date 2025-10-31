from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    company_id: str
    
    class Config:
        from_attributes = True

class CompanyCreate(BaseModel):
    name: str
    registration_no: Optional[str] = None
    tax_id: Optional[str] = None
    currency: str = "ZMW"
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class CompanyResponse(BaseModel):
    id: str
    name: str
    currency: str
    is_active: bool
    
    class Config:
        from_attributes = True

class CompanyAdminResponse(BaseModel):
    id: str
    name: str
    registration_no: Optional[str]
    tax_id: Optional[str]
    currency: str
    email: Optional[str]
    phone: Optional[str]
    is_active: bool
    subscription_plan: str
    subscription_status: str
    trial_ends_at: Optional[datetime]
    subscription_ends_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class SystemStatsResponse(BaseModel):
    total_companies: int
    active_companies: int
    trial_companies: int
    paid_companies: int
    total_users: int
    total_employees: int
    total_transactions: int
    total_revenue: float

class EmployeeCreate(BaseModel):
    employee_no: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    position: str
    department: str
    salary_base: float = 0.0
    date_joined: date

class EmployeeResponse(BaseModel):
    id: str
    employee_no: str
    first_name: str
    last_name: str
    position: str
    department: str
    employment_status: str
    
    class Config:
        from_attributes = True

class AccountCreate(BaseModel):
    code: str
    name: str
    account_type: str
    parent_id: Optional[str] = None

class AccountResponse(BaseModel):
    id: str
    code: str
    name: str
    account_type: str
    is_active: bool
    
    class Config:
        from_attributes = True

class JournalLineCreate(BaseModel):
    account_id: str
    side: str
    amount: float
    narration: Optional[str] = None

class JournalEntryCreate(BaseModel):
    date: date
    description: str
    currency: str = "ZMW"
    total_amount: float
    lines: List[JournalLineCreate]

class JournalEntryResponse(BaseModel):
    id: str
    journal_number: str
    date: date
    description: str
    total_amount: float
    status: str
    
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_employees: int
    total_accounts: int
    total_journals: int
    company_name: str

class ProductCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    unit_of_measure: str = "Unit"
    unit_price: float = 0.0
    cost_price: float = 0.0
    reorder_level: float = 0.0
    product_type: str = "storable"

class ProductResponse(BaseModel):
    id: str
    code: str
    name: str
    category: Optional[str]
    unit_price: float
    unit_of_measure: str
    
    class Config:
        from_attributes = True

class WarehouseCreate(BaseModel):
    code: str
    name: str
    location: Optional[str] = None

class WarehouseResponse(BaseModel):
    id: str
    code: str
    name: str
    location: Optional[str]
    
    class Config:
        from_attributes = True

class CustomerCreate(BaseModel):
    customer_code: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    credit_limit: float = 0.0
    payment_terms: str = "Net 30"

class CustomerResponse(BaseModel):
    id: str
    customer_code: str
    name: str
    email: Optional[str]
    phone: Optional[str]
    
    class Config:
        from_attributes = True

class SupplierCreate(BaseModel):
    supplier_code: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    payment_terms: str = "Net 30"

class SupplierResponse(BaseModel):
    id: str
    supplier_code: str
    name: str
    email: Optional[str]
    phone: Optional[str]
    
    class Config:
        from_attributes = True

class PurchaseOrderLineCreate(BaseModel):
    product_id: str
    quantity: float
    unit_price: float

class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    order_date: date
    expected_delivery: Optional[date] = None
    lines: List[PurchaseOrderLineCreate]
    notes: Optional[str] = None

class PurchaseOrderResponse(BaseModel):
    id: str
    po_number: str
    supplier_id: str
    order_date: date
    status: str
    total_amount: float
    
    class Config:
        from_attributes = True

class SalesOrderLineCreate(BaseModel):
    product_id: str
    quantity: float
    unit_price: float

class SalesOrderCreate(BaseModel):
    customer_id: str
    order_date: date
    delivery_date: Optional[date] = None
    lines: List[SalesOrderLineCreate]
    notes: Optional[str] = None

class SalesOrderResponse(BaseModel):
    id: str
    so_number: str
    customer_id: str
    order_date: date
    status: str
    total_amount: float
    
    class Config:
        from_attributes = True

class LeaveTypeCreate(BaseModel):
    name: str
    code: str
    annual_allocation: float = 0.0
    is_paid: bool = True

class LeaveTypeResponse(BaseModel):
    id: str
    name: str
    code: str
    annual_allocation: float
    is_paid: bool
    
    class Config:
        from_attributes = True

class LeaveApplicationCreate(BaseModel):
    employee_id: str
    leave_type_id: str
    start_date: date
    end_date: date
    days_requested: float
    reason: Optional[str] = None

class LeaveApplicationResponse(BaseModel):
    id: str
    application_number: str
    employee_id: str
    leave_type_id: str
    start_date: date
    end_date: date
    days_requested: float
    status: str
    
    class Config:
        from_attributes = True

class PayslipCreate(BaseModel):
    employee_id: str
    period_month: int
    period_year: int

class PayslipResponse(BaseModel):
    id: str
    payslip_number: str
    employee_id: str
    period_month: int
    period_year: int
    gross_salary: float
    net_salary: float
    status: str
    
    class Config:
        from_attributes = True

class FinancialReportRequest(BaseModel):
    start_date: date
    end_date: date
    report_type: str

class AccountBalance(BaseModel):
    account_code: str
    account_name: str
    balance: float

class FinancialReport(BaseModel):
    report_type: str
    period: str
    sections: dict

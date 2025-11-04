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
    department_id: Optional[str] = None
    salary_base: float = 0.0
    date_joined: date

class EmployeeResponse(BaseModel):
    id: str
    employee_no: str
    first_name: str
    last_name: str
    position: str
    department_id: Optional[str]
    employment_status: str
    
    class Config:
        from_attributes = True

class AccountCreate(BaseModel):
    code: str
    name: str
    account_type: str
    parent_id: Optional[str] = None
    currency: Optional[str] = None
    allow_fx_revaluation: bool = False

class AccountResponse(BaseModel):
    id: str
    code: str
    name: str
    account_type: str
    currency: Optional[str]
    allow_fx_revaluation: bool
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
    department_id: Optional[str] = None
    branch_id: Optional[str] = None
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
    department_id: Optional[str] = None
    branch_id: Optional[str] = None
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
    department_id: Optional[str] = None
    branch_id: Optional[str] = None
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

class MobileMoneyProviderCreate(BaseModel):
    provider_name: str
    provider_code: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    merchant_id: Optional[str] = None

class MobileMoneyProviderResponse(BaseModel):
    id: str
    provider_name: str
    provider_code: str
    is_active: bool
    
    class Config:
        from_attributes = True

class MobileMoneyTransactionCreate(BaseModel):
    provider_id: str
    transaction_type: str
    phone_number: str
    amount: float
    customer_name: Optional[str] = None
    description: Optional[str] = None

class MobileMoneyTransactionResponse(BaseModel):
    id: str
    transaction_ref: str
    provider_id: str
    transaction_type: str
    phone_number: str
    amount: float
    currency: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class BranchCreate(BaseModel):
    branch_code: str
    branch_name: str
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_id: Optional[str] = None
    is_main_branch: bool = False

class BranchResponse(BaseModel):
    id: str
    branch_code: str
    branch_name: str
    city: Optional[str]
    is_active: bool
    is_main_branch: bool
    
    class Config:
        from_attributes = True

class BranchTransferCreate(BaseModel):
    from_branch_id: str
    to_branch_id: str
    transfer_date: date
    lines: List[dict]
    notes: Optional[str] = None

class BranchTransferResponse(BaseModel):
    id: str
    transfer_number: str
    from_branch_id: str
    to_branch_id: str
    transfer_date: date
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class POSTerminalCreate(BaseModel):
    terminal_code: str
    terminal_name: str
    branch_id: Optional[str] = None

class POSTerminalResponse(BaseModel):
    id: str
    terminal_code: str
    terminal_name: str
    is_active: bool
    
    class Config:
        from_attributes = True

class POSSaleCreate(BaseModel):
    branch_id: Optional[str] = None
    terminal_id: Optional[str] = None
    customer_id: Optional[str] = None
    lines: List[dict]
    payment_method: str
    payment_ref: Optional[str] = None

class POSSaleResponse(BaseModel):
    id: str
    receipt_number: str
    sale_date: datetime
    total_amount: float
    payment_method: str
    status: str
    
    class Config:
        from_attributes = True

class CashierSessionCreate(BaseModel):
    terminal_id: str
    opening_cash: float

class CashierSessionResponse(BaseModel):
    id: str
    terminal_id: str
    session_start: datetime
    opening_cash: float
    status: str
    
    class Config:
        from_attributes = True

class StatutoryObligationCreate(BaseModel):
    obligation_type: str
    description: Optional[str] = None
    frequency: str  # monthly, quarterly, annually
    due_day: Optional[int] = None
    amount: Optional[float] = None
    due_date: date
    notes: Optional[str] = None

class StatutoryObligationUpdate(BaseModel):
    obligation_type: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[str] = None
    due_day: Optional[int] = None
    amount: Optional[float] = None
    status: Optional[str] = None  # pending, paid, overdue
    paid_date: Optional[date] = None
    reference_no: Optional[str] = None
    notes: Optional[str] = None

class StatutoryObligationResponse(BaseModel):
    id: str
    company_id: str
    obligation_type: str
    description: Optional[str]
    frequency: str
    due_day: Optional[int]
    amount: Optional[float]
    status: str
    due_date: date
    paid_date: Optional[date]
    reference_no: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DepartmentCreate(BaseModel):
    dept_code: str
    dept_name: str
    parent_dept_id: Optional[str] = None
    manager_id: Optional[str] = None
    cost_center_code: Optional[str] = None

class DepartmentUpdate(BaseModel):
    dept_code: Optional[str] = None
    dept_name: Optional[str] = None
    parent_dept_id: Optional[str] = None
    manager_id: Optional[str] = None
    cost_center_code: Optional[str] = None
    is_active: Optional[bool] = None

class DepartmentResponse(BaseModel):
    id: str
    company_id: str
    dept_code: str
    dept_name: str
    parent_dept_id: Optional[str]
    manager_id: Optional[str]
    cost_center_code: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class CurrencyCreate(BaseModel):
    code: str
    name: str
    symbol: Optional[str] = None
    decimal_places: int = 2
    is_base_currency: bool = False

class CurrencyResponse(BaseModel):
    id: str
    company_id: str
    code: str
    name: str
    symbol: Optional[str]
    decimal_places: int
    is_active: bool
    is_base_currency: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ExchangeRateCreate(BaseModel):
    from_currency: str
    to_currency: str
    rate: float
    rate_date: date
    rate_type: str = "spot"
    source: Optional[str] = "manual"

class ExchangeRateResponse(BaseModel):
    id: str
    company_id: str
    from_currency: str
    to_currency: str
    rate: float
    rate_date: date
    rate_type: str
    source: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class FXRevaluationRequest(BaseModel):
    revaluation_date: date
    currency: str

class FXRevaluationLineResponse(BaseModel):
    id: str
    account_id: str
    account_currency: str
    original_balance: float
    exchange_rate_old: float
    exchange_rate_new: float
    balance_base_old: float
    balance_base_new: float
    gain_loss: float
    
    class Config:
        from_attributes = True

class FXRevaluationResponse(BaseModel):
    id: str
    company_id: str
    revaluation_date: date
    currency: str
    total_gain_loss: float
    journal_entry_id: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class BankAccountCreate(BaseModel):
    account_id: str
    bank_name: str
    account_number: str
    account_name: Optional[str] = None
    branch: Optional[str] = None
    currency: str = "ZMW"
    swift_code: Optional[str] = None

class BankAccountResponse(BaseModel):
    id: str
    company_id: str
    account_id: str
    bank_name: str
    account_number: str
    currency: str
    is_active: bool
    last_reconciled_date: Optional[date]
    
    class Config:
        from_attributes = True

class BankStatementLineCreate(BaseModel):
    line_number: int
    transaction_date: date
    description: str
    reference: Optional[str] = None
    debit: float = 0.0
    credit: float = 0.0
    balance: Optional[float] = None

class BankStatementCreate(BaseModel):
    bank_account_id: str
    statement_number: str
    statement_date: date
    opening_balance: float
    closing_balance: float
    lines: List[BankStatementLineCreate]

class BankStatementResponse(BaseModel):
    id: str
    company_id: str
    bank_account_id: str
    statement_number: str
    statement_date: date
    opening_balance: float
    closing_balance: float
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class BankReconciliationCreate(BaseModel):
    bank_account_id: str
    reconciliation_date: date
    statement_id: Optional[str] = None

class BankReconciliationResponse(BaseModel):
    id: str
    company_id: str
    bank_account_id: str
    reconciliation_number: str
    reconciliation_date: date
    status: str
    total_matched_debits: float
    total_matched_credits: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class SystemSettingCreate(BaseModel):
    setting_key: str
    setting_value: Optional[str] = None
    setting_type: str = "string"
    category: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = False

class SystemSettingUpdate(BaseModel):
    setting_value: Optional[str] = None
    setting_type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

class SystemSettingResponse(BaseModel):
    id: str
    company_id: str
    setting_key: str
    setting_value: Optional[str]
    setting_type: str
    category: Optional[str]
    description: Optional[str]
    is_public: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TaxSettingCreate(BaseModel):
    tax_name: str
    tax_type: str
    jurisdiction: str = "Zambia"
    tax_brackets: Optional[List[dict]] = None
    employer_rate: float = 0.0
    employee_rate: float = 0.0
    max_amount: Optional[float] = None
    min_amount: Optional[float] = None
    applies_to: str = "gross"
    is_active: bool = True
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    tax_payable_account_id: Optional[str] = None
    tax_expense_account_id: Optional[str] = None

class TaxSettingUpdate(BaseModel):
    tax_name: Optional[str] = None
    tax_type: Optional[str] = None
    tax_brackets: Optional[List[dict]] = None
    employer_rate: Optional[float] = None
    employee_rate: Optional[float] = None
    is_active: Optional[bool] = None

class TaxSettingResponse(BaseModel):
    id: str
    company_id: str
    tax_name: str
    tax_type: str
    jurisdiction: str
    tax_brackets: Optional[List[dict]]
    employer_rate: float
    employee_rate: float
    max_amount: Optional[float]
    applies_to: str
    is_active: bool
    effective_from: Optional[date]
    created_at: datetime
    
    class Config:
        from_attributes = True

class EmailTemplateCreate(BaseModel):
    template_name: str
    template_code: str
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    available_variables: Optional[List[str]] = None
    is_active: bool = True

class EmailTemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    is_active: Optional[bool] = None

class EmailTemplateResponse(BaseModel):
    id: str
    company_id: str
    template_name: str
    template_code: str
    subject: str
    body_html: Optional[str]
    is_active: bool
    is_system: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class SalaryComponentCreate(BaseModel):
    component_code: str
    component_name: str
    component_type: str
    calculation_method: str = "fixed"
    default_amount: float = 0.0
    percentage_of: Optional[str] = None
    is_taxable: bool = True
    is_pensionable: bool = False
    include_in_gross: bool = True
    is_statutory: bool = False
    statutory_type: Optional[str] = None
    expense_account_id: Optional[str] = None
    payable_account_id: Optional[str] = None
    is_active: bool = True
    display_order: int = 0

class SalaryComponentUpdate(BaseModel):
    component_name: Optional[str] = None
    default_amount: Optional[float] = None
    is_active: Optional[bool] = None

class SalaryComponentResponse(BaseModel):
    id: str
    company_id: str
    component_code: str
    component_name: str
    component_type: str
    calculation_method: str
    default_amount: float
    is_taxable: bool
    is_statutory: bool
    is_active: bool
    display_order: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ApprovalWorkflowRuleCreate(BaseModel):
    workflow_name: str
    entity_type: str
    conditions: Optional[dict] = None
    approval_chain: Optional[List[dict]] = None
    notify_on_submit: bool = True
    is_active: bool = True
    priority: int = 0

class ApprovalWorkflowRuleUpdate(BaseModel):
    workflow_name: Optional[str] = None
    conditions: Optional[dict] = None
    approval_chain: Optional[List[dict]] = None
    is_active: Optional[bool] = None

class ApprovalWorkflowRuleResponse(BaseModel):
    id: str
    company_id: str
    workflow_name: str
    entity_type: str
    conditions: Optional[dict]
    approval_chain: Optional[List[dict]]
    is_active: bool
    priority: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class LeaveTypeConfigurationCreate(BaseModel):
    leave_type_id: str
    accrual_method: str = "annual"
    accrual_rate: float = 0.0
    max_accrual: Optional[float] = None
    carry_forward_allowed: bool = True
    min_days_per_request: float = 0.5
    requires_approval: bool = True
    approval_levels: int = 1
    exclude_weekends: bool = True
    exclude_holidays: bool = True
    is_paid: bool = True
    pay_percentage: float = 100.0

class LeaveTypeConfigurationUpdate(BaseModel):
    accrual_method: Optional[str] = None
    accrual_rate: Optional[float] = None
    requires_approval: Optional[bool] = None
    is_paid: Optional[bool] = None

class LeaveTypeConfigurationResponse(BaseModel):
    id: str
    company_id: str
    leave_type_id: str
    accrual_method: str
    accrual_rate: float
    requires_approval: bool
    is_paid: bool
    pay_percentage: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationCreate(BaseModel):
    user_id: str
    title: str
    message: str
    notification_type: str = "info"
    channel: str = "in_app"
    priority: str = "normal"
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    expires_at: Optional[datetime] = None

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    
class NotificationResponse(BaseModel):
    id: str
    company_id: str
    user_id: str
    title: str
    message: str
    notification_type: str
    channel: str
    priority: str
    is_read: bool
    read_at: Optional[datetime]
    related_entity_type: Optional[str]
    related_entity_id: Optional[str]
    action_url: Optional[str]
    action_label: Optional[str]
    email_sent: bool
    email_sent_at: Optional[datetime]
    sms_sent: bool
    sms_sent_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AuditLogCreate(BaseModel):
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    changes: Optional[dict] = None
    status: str = "success"
    error_message: Optional[str] = None

class AuditLogResponse(BaseModel):
    id: str
    company_id: str
    user_id: Optional[str]
    user_email: Optional[str]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    changes: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    status: str
    error_message: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True

class AuditLogFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    status: Optional[str] = None


# ============================================================================
# SALES & PROCUREMENT SCHEMAS (Phase 4B)
# ============================================================================

class CustomerCreate(BaseModel):
    customer_code: str
    customer_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Zambia"
    tax_id: Optional[str] = None
    credit_limit: Optional[float] = 0
    payment_terms_days: Optional[int] = 30
    is_active: Optional[bool] = True

class CustomerUpdate(BaseModel):
    customer_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    credit_limit: Optional[float] = None
    payment_terms_days: Optional[int] = None
    is_active: Optional[bool] = None

class SupplierCreate(BaseModel):
    supplier_code: str
    supplier_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Zambia"
    tax_id: Optional[str] = None
    payment_terms_days: Optional[int] = 30
    is_active: Optional[bool] = True

class SupplierUpdate(BaseModel):
    supplier_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms_days: Optional[int] = None
    is_active: Optional[bool] = None

class SalesOrderLineCreate(BaseModel):
    product_id: Optional[str] = None
    description: str
    quantity: float
    unit_price: float
    tax_rate: Optional[float] = 0.16

class SalesOrderCreate(BaseModel):
    customer_id: str
    order_date: Optional[date] = None
    delivery_date: Optional[date] = None
    currency: Optional[str] = "ZMW"
    notes: Optional[str] = None
    lines: List[SalesOrderLineCreate]

class PurchaseOrderLineCreate(BaseModel):
    product_id: Optional[str] = None
    description: str
    quantity: float
    unit_price: float
    tax_rate: Optional[float] = 0.16

class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    order_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    currency: Optional[str] = "ZMW"
    notes: Optional[str] = None
    lines: List[PurchaseOrderLineCreate]


# ============================================================================
# INVENTORY SCHEMAS
# ============================================================================

class ProductCreate(BaseModel):
    product_code: str
    product_name: str
    description: Optional[str] = None
    product_type: str = "goods"  # goods, service, raw_material, finished_goods
    unit_of_measure: str = "unit"
    cost_price: Optional[float] = 0
    selling_price: Optional[float] = 0
    barcode: Optional[str] = None
    track_inventory: Optional[bool] = True
    track_batches: Optional[bool] = False
    track_serials: Optional[bool] = False
    is_active: Optional[bool] = True

class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    description: Optional[str] = None
    product_type: Optional[str] = None
    unit_of_measure: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    barcode: Optional[str] = None
    track_inventory: Optional[bool] = None
    track_batches: Optional[bool] = None
    track_serials: Optional[bool] = None
    is_active: Optional[bool] = None

class WarehouseCreate(BaseModel):
    warehouse_code: str
    warehouse_name: str
    location: Optional[str] = None
    is_active: Optional[bool] = True

class StockMovementCreate(BaseModel):
    product_id: str
    warehouse_id: str
    movement_type: str  # purchase, sale, production, adjustment_in, adjustment_out, transfer_in, transfer_out
    quantity: float
    unit_cost: Optional[float] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None
    movement_date: Optional[date] = None


# ============================================================================
# TAX/VAT SCHEMAS
# ============================================================================

class TaxSettingCreate(BaseModel):
    tax_type: str  # PAYE, VAT, WHT, Turnover, Excise
    tax_name: str
    tax_jurisdiction: Optional[str] = "Zambia"
    tax_rate: Optional[float] = None
    tax_brackets: Optional[dict] = None
    tax_payable_account_id: Optional[str] = None
    tax_expense_account_id: Optional[str] = None
    effective_from: date
    effective_to: Optional[date] = None
    filing_frequency: Optional[str] = "monthly"
    filing_due_day: Optional[int] = None
    is_active: Optional[bool] = True

class TaxSettingUpdate(BaseModel):
    tax_name: Optional[str] = None
    tax_jurisdiction: Optional[str] = None
    tax_rate: Optional[float] = None
    tax_brackets: Optional[dict] = None
    tax_payable_account_id: Optional[str] = None
    tax_expense_account_id: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    filing_frequency: Optional[str] = None
    filing_due_day: Optional[int] = None
    is_active: Optional[bool] = None

class TaxCalculation(BaseModel):
    tax_setting_id: str
    amount: float

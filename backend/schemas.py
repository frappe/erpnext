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

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
    company_id = Column(String, ForeignKey("companies.id"))
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

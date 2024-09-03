from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .doctype import Base
import enum

class AccountType(enum.Enum):
    ASSET = "Asset"
    LIABILITY = "Liability"
    INCOME = "Income"
    EXPENSE = "Expense"
    EQUITY = "Equity"

class Account(Base):
    __tablename__ = 'tabAccount'

    name = Column(String(140), primary_key=True)
    account_name = Column(String(140))
    parent_account = Column(String(140), ForeignKey('tabAccount.name'))
    root_type = Column(Enum(AccountType))
    is_group = Column(Boolean, default=False)
    company = Column(String(140), ForeignKey('tabCompany.name'))
    
    # Relationships
    child_accounts = relationship("Account", back_populates="parent")
    parent = relationship("Account", back_populates="child_accounts", remote_side=[name])

class JournalEntry(Base):
    __tablename__ = 'tabJournal Entry'

    name = Column(String(140), primary_key=True)
    posting_date = Column(DateTime)
    company = Column(String(140), ForeignKey('tabCompany.name'))
    total_debit = Column(Float(precision=2), default=0)
    total_credit = Column(Float(precision=2), default=0)
    
    # Relationships
    accounts = relationship("JournalEntryAccount", back_populates="journal_entry")

class JournalEntryAccount(Base):
    __tablename__ = 'tabJournal Entry Account'

    name = Column(String(140), primary_key=True)
    parent = Column(String(140), ForeignKey('tabJournal Entry.name'))
    account = Column(String(140), ForeignKey('tabAccount.name'))
    debit = Column(Float(precision=2), default=0)
    credit = Column(Float(precision=2), default=0)
    
    # Relationships
    journal_entry = relationship("JournalEntry", back_populates="accounts")
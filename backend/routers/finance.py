"""
Finance & Accounting API Routes

Endpoints for:
- Chart of Accounts (COA)
- Journal Entries
- Accounts Receivable (AR)
- Accounts Payable (AP)
- Financial Reports
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel
from decimal import Decimal

import models
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/finance", tags=["Finance"])


class AccountCreate(BaseModel):
    code: str
    name: str
    account_type: str  # asset, liability, equity, revenue, expense
    parent_code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class JournalEntryCreate(BaseModel):
    entry_date: date
    reference: str
    description: str
    lines: List[dict]  # [{account_id, debit, credit, description}]
    source_type: Optional[str] = None
    source_id: Optional[str] = None


class InvoiceCreate(BaseModel):
    customer_id: str
    invoice_date: date
    due_date: date
    currency: str = "ZMW"
    lines: List[dict]  # [{description, quantity, unit_price, tax_rate}]
    notes: Optional[str] = None


class PaymentCreate(BaseModel):
    invoice_id: Optional[str] = None
    customer_id: Optional[str] = None
    supplier_id: Optional[str] = None
    payment_date: date
    amount: float
    payment_method: str
    reference: Optional[str] = None
    notes: Optional[str] = None


@router.get("/accounts")
def list_accounts(
    account_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List chart of accounts"""
    query = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id
    )
    
    if account_type:
        query = query.filter(models.Account.account_type == account_type)
    if is_active is not None:
        query = query.filter(models.Account.is_active == is_active)
    
    accounts = query.order_by(models.Account.code).all()
    
    return {"success": True, "count": len(accounts), "accounts": accounts}


@router.post("/accounts")
def create_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create new account"""
    # Check if code exists
    existing = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id,
        models.Account.code == data.code
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Account code already exists")
    
    # Get parent account if specified
    parent_id = None
    if data.parent_code:
        parent = db.query(models.Account).filter(
            models.Account.company_id == current_user.company_id,
            models.Account.code == data.parent_code
        ).first()
        if parent:
            parent_id = parent.id
    
    account = models.Account(
        company_id=current_user.company_id,
        code=data.code,
        name=data.name,
        account_type=data.account_type,
        parent_id=parent_id,
        description=data.description,
        is_active=data.is_active
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    
    return {"success": True, "account": account}


@router.get("/accounts/{account_id}")
def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get account details with balance"""
    account = db.query(models.Account).filter(
        models.Account.id == account_id,
        models.Account.company_id == current_user.company_id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Calculate balance
    debits = db.query(func.sum(models.JournalEntryLine.debit)).filter(
        models.JournalEntryLine.account_id == account_id
    ).scalar() or 0
    
    credits = db.query(func.sum(models.JournalEntryLine.credit)).filter(
        models.JournalEntryLine.account_id == account_id
    ).scalar() or 0
    
    balance = debits - credits
    
    return {
        "success": True,
        "account": account,
        "balance": {
            "debits": float(debits),
            "credits": float(credits),
            "balance": float(balance)
        }
    }


@router.put("/accounts/{account_id}")
def update_account(
    account_id: str,
    data: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update account"""
    account = db.query(models.Account).filter(
        models.Account.id == account_id,
        models.Account.company_id == current_user.company_id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    for field, value in data.dict(exclude_unset=True).items():
        setattr(account, field, value)
    
    db.commit()
    db.refresh(account)
    
    return {"success": True, "account": account}


@router.post("/journal-entries")
def create_journal_entry(
    data: JournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create journal entry with double-entry validation"""
    # Validate double-entry (debits = credits)
    total_debits = sum(line.get("debit", 0) for line in data.lines)
    total_credits = sum(line.get("credit", 0) for line in data.lines)
    
    if abs(total_debits - total_credits) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Entry not balanced. Debits: {total_debits}, Credits: {total_credits}"
        )
    
    # Generate entry number
    last_entry = db.query(models.JournalEntry).filter(
        models.JournalEntry.company_id == current_user.company_id
    ).order_by(models.JournalEntry.created_at.desc()).first()
    
    if last_entry and last_entry.entry_number:
        try:
            last_num = int(last_entry.entry_number.split('-')[1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    entry_number = f"JE-{new_num:06d}"
    
    # Create journal entry
    entry = models.JournalEntry(
        company_id=current_user.company_id,
        entry_number=entry_number,
        entry_date=data.entry_date,
        reference=data.reference,
        description=data.description,
        source_type=data.source_type,
        source_id=data.source_id,
        status="draft",
        created_by=current_user.id
    )
    
    db.add(entry)
    db.flush()
    
    # Create lines
    for line_data in data.lines:
        line = models.JournalEntryLine(
            company_id=current_user.company_id,
            entry_id=entry.id,
            account_id=line_data["account_id"],
            debit=line_data.get("debit", 0),
            credit=line_data.get("credit", 0),
            description=line_data.get("description", "")
        )
        db.add(line)
    
    db.commit()
    db.refresh(entry)
    
    return {"success": True, "entry": entry, "entry_number": entry_number}


@router.get("/journal-entries")
def list_journal_entries(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List journal entries"""
    query = db.query(models.JournalEntry).filter(
        models.JournalEntry.company_id == current_user.company_id
    )
    
    if from_date:
        query = query.filter(models.JournalEntry.entry_date >= from_date)
    if to_date:
        query = query.filter(models.JournalEntry.entry_date <= to_date)
    if status:
        query = query.filter(models.JournalEntry.status == status)
    
    entries = query.order_by(models.JournalEntry.entry_date.desc()).limit(limit).all()
    
    return {"success": True, "count": len(entries), "entries": entries}


@router.get("/journal-entries/{entry_id}")
def get_journal_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get journal entry with lines"""
    entry = db.query(models.JournalEntry).filter(
        models.JournalEntry.id == entry_id,
        models.JournalEntry.company_id == current_user.company_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    lines = db.query(models.JournalEntryLine).filter(
        models.JournalEntryLine.entry_id == entry_id
    ).all()
    
    return {"success": True, "entry": entry, "lines": lines}


@router.post("/journal-entries/{entry_id}/post")
def post_journal_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Post journal entry (mark as posted, cannot be edited)"""
    entry = db.query(models.JournalEntry).filter(
        models.JournalEntry.id == entry_id,
        models.JournalEntry.company_id == current_user.company_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    if entry.status == "posted":
        raise HTTPException(status_code=400, detail="Entry already posted")
    
    entry.status = "posted"
    entry.posted_at = datetime.now()
    entry.posted_by = current_user.id
    
    db.commit()
    
    return {"success": True, "message": "Journal entry posted successfully"}


@router.get("/reports/trial-balance")
def trial_balance(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Generate trial balance report"""
    if not as_of_date:
        as_of_date = date.today()
    
    # Get all accounts
    accounts = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id,
        models.Account.is_active == True
    ).order_by(models.Account.code).all()
    
    trial_balance_data = []
    total_debits = 0
    total_credits = 0
    
    for account in accounts:
        # Get sum of debits and credits up to as_of_date
        debits = db.query(func.sum(models.JournalEntryLine.debit)).join(
            models.JournalEntry
        ).filter(
            models.JournalEntryLine.account_id == account.id,
            models.JournalEntry.entry_date <= as_of_date,
            models.JournalEntry.status == "posted"
        ).scalar() or 0
        
        credits = db.query(func.sum(models.JournalEntryLine.credit)).join(
            models.JournalEntry
        ).filter(
            models.JournalEntryLine.account_id == account.id,
            models.JournalEntry.entry_date <= as_of_date,
            models.JournalEntry.status == "posted"
        ).scalar() or 0
        
        balance = debits - credits
        
        if balance != 0:
            trial_balance_data.append({
                "code": account.code,
                "name": account.name,
                "account_type": account.account_type,
                "debit": float(balance) if balance > 0 else 0,
                "credit": float(-balance) if balance < 0 else 0
            })
            
            if balance > 0:
                total_debits += balance
            else:
                total_credits += -balance
    
    return {
        "success": True,
        "as_of_date": as_of_date,
        "accounts": trial_balance_data,
        "totals": {
            "total_debits": float(total_debits),
            "total_credits": float(total_credits),
            "difference": float(total_debits - total_credits)
        }
    }


@router.get("/reports/income-statement")
def income_statement(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Generate Profit & Loss statement"""
    # Get revenue accounts
    revenue_accounts = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id,
        models.Account.account_type == "revenue",
        models.Account.is_active == True
    ).all()
    
    # Get expense accounts
    expense_accounts = db.query(models.Account).filter(
        models.Account.company_id == current_user.company_id,
        models.Account.account_type == "expense",
        models.Account.is_active == True
    ).all()
    
    revenue_data = []
    total_revenue = 0
    
    for account in revenue_accounts:
        credits = db.query(func.sum(models.JournalEntryLine.credit)).join(
            models.JournalEntry
        ).filter(
            models.JournalEntryLine.account_id == account.id,
            models.JournalEntry.entry_date >= from_date,
            models.JournalEntry.entry_date <= to_date,
            models.JournalEntry.status == "posted"
        ).scalar() or 0
        
        debits = db.query(func.sum(models.JournalEntryLine.debit)).join(
            models.JournalEntry
        ).filter(
            models.JournalEntryLine.account_id == account.id,
            models.JournalEntry.entry_date >= from_date,
            models.JournalEntry.entry_date <= to_date,
            models.JournalEntry.status == "posted"
        ).scalar() or 0
        
        net = credits - debits
        
        if net != 0:
            revenue_data.append({
                "code": account.code,
                "name": account.name,
                "amount": float(net)
            })
            total_revenue += net
    
    expense_data = []
    total_expenses = 0
    
    for account in expense_accounts:
        debits = db.query(func.sum(models.JournalEntryLine.debit)).join(
            models.JournalEntry
        ).filter(
            models.JournalEntryLine.account_id == account.id,
            models.JournalEntry.entry_date >= from_date,
            models.JournalEntry.entry_date <= to_date,
            models.JournalEntry.status == "posted"
        ).scalar() or 0
        
        credits = db.query(func.sum(models.JournalEntryLine.credit)).join(
            models.JournalEntry
        ).filter(
            models.JournalEntryLine.account_id == account.id,
            models.JournalEntry.entry_date >= from_date,
            models.JournalEntry.entry_date <= to_date,
            models.JournalEntry.status == "posted"
        ).scalar() or 0
        
        net = debits - credits
        
        if net != 0:
            expense_data.append({
                "code": account.code,
                "name": account.name,
                "amount": float(net)
            })
            total_expenses += net
    
    net_profit = total_revenue - total_expenses
    
    return {
        "success": True,
        "period": {"from": from_date, "to": to_date},
        "revenue": {
            "accounts": revenue_data,
            "total": float(total_revenue)
        },
        "expenses": {
            "accounts": expense_data,
            "total": float(total_expenses)
        },
        "net_profit": float(net_profit)
    }


@router.get("/reports/balance-sheet")
def balance_sheet(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Generate Balance Sheet"""
    if not as_of_date:
        as_of_date = date.today()
    
    def get_account_balance(account_type):
        accounts = db.query(models.Account).filter(
            models.Account.company_id == current_user.company_id,
            models.Account.account_type == account_type,
            models.Account.is_active == True
        ).all()
        
        account_data = []
        total = 0
        
        for account in accounts:
            debits = db.query(func.sum(models.JournalEntryLine.debit)).join(
                models.JournalEntry
            ).filter(
                models.JournalEntryLine.account_id == account.id,
                models.JournalEntry.entry_date <= as_of_date,
                models.JournalEntry.status == "posted"
            ).scalar() or 0
            
            credits = db.query(func.sum(models.JournalEntryLine.credit)).join(
                models.JournalEntry
            ).filter(
                models.JournalEntryLine.account_id == account.id,
                models.JournalEntry.entry_date <= as_of_date,
                models.JournalEntry.status == "posted"
            ).scalar() or 0
            
            balance = debits - credits
            
            if balance != 0:
                account_data.append({
                    "code": account.code,
                    "name": account.name,
                    "amount": float(balance)
                })
                total += balance
        
        return account_data, total
    
    assets, total_assets = get_account_balance("asset")
    liabilities, total_liabilities = get_account_balance("liability")
    equity, total_equity = get_account_balance("equity")
    
    return {
        "success": True,
        "as_of_date": as_of_date,
        "assets": {
            "accounts": assets,
            "total": float(total_assets)
        },
        "liabilities": {
            "accounts": liabilities,
            "total": float(total_liabilities)
        },
        "equity": {
            "accounts": equity,
            "total": float(total_equity)
        },
        "total_liabilities_and_equity": float(total_liabilities + total_equity)
    }


# ============================================================================
# NEW COMPACT JOURNAL ENTRY ENDPOINTS (per Finance PDF spec)
# ============================================================================

from services.finance import JournalEntryService
import schemas


@router.post("/journals/compact", response_model=schemas.JournalEntryDetailResponse)
def create_compact_journal_entry(
    data: schemas.CompactJournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create journal entry using COMPACT format (per Finance PDF spec)
    
    Single amount with both debit and credit accounts specified.
    System automatically expands to double-entry format internally.
    
    Example:
    {
      "date": "2025-11-05",
      "description": "Sale of goods to Customer A",
      "currency": "ZMW",
      "total_amount": 1200.00,
      "entries": {
        "debits": [{"account_code": "1000-AR", "amount": 1200, "narration": "Invoice #001"}],
        "credits": [{"account_code": "4000-SALES", "amount": 1200, "narration": "Goods sold"}]
      },
      "auto_post": false
    }
    """
    service = JournalEntryService(db, current_user.company_id, current_user.id)
    
    # Generate journal number if not provided
    journal_number = data.journal_number or service.generate_journal_number()
    
    # Create compact journal entry
    journal_entry = service.create_journal_entry(
        journal_number=journal_number,
        entry_date=data.date,
        description=data.description,
        currency=data.currency,
        data={"entries": data.entries.dict()},
        department_id=data.department_id,
        branch_id=data.branch_id,
        source_type=data.source_type,
        source_id=data.source_id,
        auto_post=data.auto_post
    )
    
    # Return detailed response with lines
    return service.get_journal_entry(journal_entry.id)


@router.post("/journals/legacy", response_model=schemas.JournalEntryDetailResponse)
def create_legacy_journal_entry(
    data: schemas.LegacyJournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create journal entry using LEGACY format (traditional double-entry)
    
    Example:
    {
      "date": "2025-11-05",
      "description": "Sale of goods",
      "currency": "ZMW",
      "lines": [
        {"account_code": "1000-AR", "side": "debit", "amount": 1200, "narration": "Invoice"},
        {"account_code": "4000-SALES", "side": "credit", "amount": 1200, "narration": "Sale"}
      ],
      "auto_post": false
    }
    """
    service = JournalEntryService(db, current_user.company_id, current_user.id)
    
    # Generate journal number if not provided
    journal_number = data.journal_number or service.generate_journal_number()
    
    # Create legacy journal entry
    journal_entry = service.create_journal_entry(
        journal_number=journal_number,
        entry_date=data.date,
        description=data.description,
        currency=data.currency,
        data={"lines": [line.dict() for line in data.lines]},
        department_id=data.department_id,
        branch_id=data.branch_id,
        source_type=data.source_type,
        source_id=data.source_id,
        auto_post=data.auto_post
    )
    
    # Return detailed response with lines
    return service.get_journal_entry(journal_entry.id)


@router.get("/journals/{journal_id}", response_model=schemas.JournalEntryDetailResponse)
def get_journal_detail(
    journal_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get journal entry with all line details"""
    service = JournalEntryService(db, current_user.company_id, current_user.id)
    return service.get_journal_entry(journal_id)


@router.post("/journals/{journal_id}/post", response_model=schemas.JournalEntryDetailResponse)
def post_journal(
    journal_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Post a journal entry (change status from draft to posted)
    Posted entries cannot be edited - only reversed
    """
    service = JournalEntryService(db, current_user.company_id, current_user.id)
    journal = service.post_journal_entry(journal_id)
    return service.get_journal_entry(journal.id)


@router.post("/journals/reverse", response_model=schemas.JournalEntryDetailResponse)
def reverse_journal(
    data: schemas.JournalEntryReversalRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Reverse a journal entry by creating a reversing entry
    
    Per audit trail requirement: entries cannot be deleted, only reversed.
    This creates a new entry with swapped debits/credits.
    """
    service = JournalEntryService(db, current_user.company_id, current_user.id)
    reversal = service.reverse_journal_entry(
        journal_id=data.journal_id,
        reversal_date=data.reversal_date,
        reversal_reason=data.reversal_reason
    )
    return service.get_journal_entry(reversal.id)


@router.get("/journals")
def list_journals(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    status: Optional[str] = None,
    department_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List journal entries with filters"""
    query = db.query(models.JournalEntry).filter(
        models.JournalEntry.company_id == current_user.company_id
    )
    
    if from_date:
        query = query.filter(models.JournalEntry.date >= from_date)
    if to_date:
        query = query.filter(models.JournalEntry.date <= to_date)
    if status:
        query = query.filter(models.JournalEntry.status == status)
    if department_id:
        query = query.filter(models.JournalEntry.department_id == department_id)
    
    total_count = query.count()
    journals = query.order_by(models.JournalEntry.date.desc()).limit(limit).offset(offset).all()
    
    return {
        "success": True,
        "total_count": total_count,
        "count": len(journals),
        "limit": limit,
        "offset": offset,
        "journals": journals
    }


# ============================================================================
# APPROVAL WORKFLOW ENDPOINTS (per Finance PDF spec)
# ============================================================================

from services.finance import ApprovalWorkflowEngine


@router.post("/approvals/submit", response_model=schemas.ApprovalResponse)
def submit_for_approval(
    data: schemas.ApprovalSubmitRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Submit a document for approval (draft → pending_approval)
    
    Approval levels are automatically determined by amount:
    - Basic (< 10,000 ZMW): Any manager can approve
    - Medium (10,000 - 100,000 ZMW): Department manager approval
    - High (> 100,000 ZMW): Finance director approval
    
    Example:
    {
      "document_type": "journal_entry",
      "document_id": "abc123",
      "notes": "Please review and approve"
    }
    """
    workflow = ApprovalWorkflowEngine(db, current_user.company_id, current_user.id)
    result = workflow.submit_for_approval(
        document_type=data.document_type,
        document_id=data.document_id,
        notes=data.notes
    )
    return result


@router.post("/approvals/approve", response_model=schemas.ApprovalResponse)
def approve_document(
    data: schemas.ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Approve a document (pending_approval → approved)
    
    User must have permission to approve based on approval level.
    Cannot approve own submission (segregation of duties).
    
    Example:
    {
      "document_type": "journal_entry",
      "document_id": "abc123",
      "notes": "Approved - looks good"
    }
    """
    workflow = ApprovalWorkflowEngine(db, current_user.company_id, current_user.id)
    result = workflow.approve_document(
        document_type=data.document_type,
        document_id=data.document_id,
        approval_notes=data.notes
    )
    return result


@router.post("/approvals/reject", response_model=schemas.ApprovalResponse)
def reject_document(
    data: schemas.ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Reject a document (pending_approval → rejected)
    
    User must have permission to reject based on approval level.
    Rejection reason is required in notes field.
    
    Example:
    {
      "document_type": "journal_entry",
      "document_id": "abc123",
      "notes": "Incorrect account codes - please revise"
    }
    """
    if not data.notes:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    workflow = ApprovalWorkflowEngine(db, current_user.company_id, current_user.id)
    result = workflow.reject_document(
        document_type=data.document_type,
        document_id=data.document_id,
        rejection_reason=data.notes
    )
    return result


@router.get("/approvals/pending", response_model=List[schemas.PendingApprovalItem])
def get_pending_approvals(
    document_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get pending approvals for current user
    
    Returns only documents that the current user has permission to approve.
    Excludes self-submitted requests (segregation of duties).
    """
    workflow = ApprovalWorkflowEngine(db, current_user.company_id, current_user.id)
    pending = workflow.get_pending_approvals(document_type=document_type)
    return pending


# ============================================================================
# PERIOD MANAGEMENT ENDPOINTS (per Finance PDF spec)
# ============================================================================

from services.finance import PeriodManagementService


@router.post("/periods", response_model=schemas.AccountingPeriodResponse)
def create_accounting_period(
    data: schemas.AccountingPeriodCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new accounting period
    
    Example:
    {
      "period_name": "January 2025",
      "start_date": "2025-01-01",
      "end_date": "2025-01-31",
      "period_type": "monthly",
      "fiscal_year": 2025
    }
    """
    service = PeriodManagementService(db, current_user.company_id, current_user.id)
    period = service.create_period(
        period_name=data.period_name,
        start_date=data.start_date,
        end_date=data.end_date,
        period_type=data.period_type,
        fiscal_year=data.fiscal_year
    )
    return period


@router.post("/periods/auto-create", response_model=List[schemas.AccountingPeriodResponse])
def auto_create_periods(
    data: schemas.AccountingPeriodAutoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Auto-create accounting periods for a year
    
    Example (create all 12 months for 2025):
    {
      "start_year": 2025,
      "num_years": 1,
      "period_type": "monthly"
    }
    
    Example (create quarters for 2025-2026):
    {
      "start_year": 2025,
      "num_years": 2,
      "period_type": "quarterly"
    }
    """
    service = PeriodManagementService(db, current_user.company_id, current_user.id)
    periods = service.auto_create_periods(
        start_year=data.start_year,
        num_years=data.num_years,
        period_type=data.period_type
    )
    return periods


@router.post("/periods/close", response_model=schemas.AccountingPeriodResponse)
def close_accounting_period(
    data: schemas.AccountingPeriodClose,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Close an accounting period (open → closed)
    
    Validates:
    - No draft journal entries in period
    - Period is currently open
    
    Closed periods:
    - No new transactions allowed
    - Existing transactions can be adjusted (with approval)
    - Can be reopened if needed
    
    Example:
    {
      "period_id": "abc123",
      "close_notes": "Month-end close complete"
    }
    """
    service = PeriodManagementService(db, current_user.company_id, current_user.id)
    period = service.close_period(
        period_id=data.period_id,
        close_notes=data.close_notes
    )
    return period


@router.post("/periods/lock", response_model=schemas.AccountingPeriodResponse)
def lock_accounting_period(
    data: schemas.AccountingPeriodLock,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Lock an accounting period (closed → locked)
    
    WARNING: Locked periods are IMMUTABLE
    - Cannot be unlocked (requires database intervention)
    - All journal entries in period are also locked
    - Used for year-end close and audit compliance
    
    Validates:
    - Period must be closed first
    
    Example:
    {
      "period_id": "abc123",
      "lock_notes": "Year-end close 2024 - audited"
    }
    """
    service = PeriodManagementService(db, current_user.company_id, current_user.id)
    period = service.lock_period(
        period_id=data.period_id,
        lock_notes=data.lock_notes
    )
    return period


@router.post("/periods/reopen", response_model=schemas.AccountingPeriodResponse)
def reopen_accounting_period(
    data: schemas.AccountingPeriodReopen,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Reopen a closed accounting period (closed → open)
    
    Note: LOCKED periods CANNOT be reopened
    Requires a reason for audit trail
    
    Example:
    {
      "period_id": "abc123",
      "reopen_reason": "Adjustment required for missed invoice"
    }
    """
    service = PeriodManagementService(db, current_user.company_id, current_user.id)
    period = service.reopen_period(
        period_id=data.period_id,
        reopen_reason=data.reopen_reason
    )
    return period


@router.get("/periods", response_model=List[schemas.AccountingPeriodResponse])
def list_accounting_periods(
    fiscal_year: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    List all accounting periods for the company
    
    Query params:
    - fiscal_year: Filter by fiscal year (e.g., 2025)
    - status: Filter by status (open, closed, locked)
    """
    service = PeriodManagementService(db, current_user.company_id, current_user.id)
    periods = service.get_all_periods(
        fiscal_year=fiscal_year,
        status=status
    )
    return periods


@router.get("/periods/{period_id}", response_model=schemas.AccountingPeriodResponse)
def get_accounting_period(
    period_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get details of a specific accounting period"""
    period = db.query(models.AccountingPeriod).filter(
        models.AccountingPeriod.id == period_id,
        models.AccountingPeriod.company_id == current_user.company_id
    ).first()
    
    if not period:
        raise HTTPException(status_code=404, detail="Accounting period not found")
    
    return period

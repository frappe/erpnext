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


# ============================================================================
# FX REVALUATION ENDPOINTS (per Finance PDF spec)
# ============================================================================

from services.finance import (
    FXRevaluationService,
    SmartInvoiceService,
    PaymentMatchingEngine,
    FixedAssetDepreciationService,
    IntercompanyTransactionService,
    FinancialReportService
)
from fastapi.responses import Response


@router.post("/fx/rates", response_model=schemas.ExchangeRateResponse)
def add_exchange_rate(
    data: schemas.ExchangeRateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Add or update exchange rate for a currency pair
    
    Example (1 USD = 27.5 ZMW on Nov 5, 2025):
    {
      "from_currency": "USD",
      "to_currency": "ZMW",
      "rate": 27.5,
      "rate_date": "2025-11-05",
      "rate_type": "official",
      "source": "Bank of Zambia"
    }
    """
    service = FXRevaluationService(db, current_user.company_id, current_user.id)
    rate = service.add_exchange_rate(
        from_currency=data.from_currency,
        to_currency=data.to_currency,
        rate=data.rate,
        rate_date=data.rate_date,
        rate_type=data.rate_type
    )
    return rate


@router.get("/fx/rates", response_model=List[schemas.ExchangeRateResponse])
def list_exchange_rates(
    from_currency: Optional[str] = None,
    to_currency: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    List all exchange rates for the company
    
    Query params:
    - from_currency: Filter by source currency (e.g., USD)
    - to_currency: Filter by target currency (e.g., ZMW)
    - from_date: Filter rates from this date
    - to_date: Filter rates to this date
    """
    query = db.query(models.ExchangeRate).filter(
        models.ExchangeRate.company_id == current_user.company_id
    )
    
    if from_currency:
        query = query.filter(models.ExchangeRate.from_currency == from_currency)
    if to_currency:
        query = query.filter(models.ExchangeRate.to_currency == to_currency)
    if from_date:
        query = query.filter(models.ExchangeRate.rate_date >= from_date)
    if to_date:
        query = query.filter(models.ExchangeRate.rate_date <= to_date)
    
    rates = query.order_by(models.ExchangeRate.rate_date.desc()).all()
    return rates


@router.get("/fx/rates/{currency_pair}/{rate_date}")
def get_exchange_rate(
    currency_pair: str,  # Format: USD-ZMW
    rate_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get specific exchange rate for a currency pair and date
    
    URL format: /fx/rates/USD-ZMW/2025-11-05
    
    Returns the rate or the most recent rate before the specified date.
    """
    try:
        from_currency, to_currency = currency_pair.split("-")
    except:
        raise HTTPException(
            status_code=400,
            detail="Invalid currency pair format. Use: USD-ZMW"
        )
    
    service = FXRevaluationService(db, current_user.company_id, current_user.id)
    rate_value = service.get_exchange_rate(from_currency, to_currency, rate_date)
    
    if rate_value is None:
        raise HTTPException(
            status_code=404,
            detail=f"No exchange rate found for {currency_pair} on or before {rate_date}"
        )
    
    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": rate_value,
        "rate_date": rate_date
    }


@router.post("/fx/revaluate", response_model=schemas.FXRevaluationResponse)
def perform_fx_revaluation(
    data: schemas.FXRevaluationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Perform FX revaluation for all foreign currency accounts
    
    This calculates unrealized gains/losses and optionally creates
    a revaluation journal entry.
    
    Process:
    1. Identify accounts marked for FX revaluation
    2. Get current balances in foreign currency
    3. Apply current exchange rate vs. book rate
    4. Calculate unrealized gain/loss
    5. Create revaluation journal entry (if requested)
    
    Example (revalue all USD accounts as of Nov 5, 2025):
    {
      "revaluation_date": "2025-11-05",
      "currencies": ["USD"],
      "create_journal": true
    }
    
    Example (revalue all foreign currencies):
    {
      "revaluation_date": "2025-11-05",
      "currencies": null,
      "create_journal": true
    }
    """
    service = FXRevaluationService(db, current_user.company_id, current_user.id)
    result = service.perform_revaluation(
        revaluation_date=data.revaluation_date,
        currencies=data.currencies,
        create_journal=data.create_journal
    )
    return result


@router.get("/fx/revaluation-history")
def get_revaluation_history(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get history of FX revaluations
    
    Returns all journal entries created by the FX revaluation process.
    """
    service = FXRevaluationService(db, current_user.company_id, current_user.id)
    history = service.get_revaluation_history(from_date=from_date, to_date=to_date)
    return {
        "success": True,
        "count": len(history),
        "revaluations": history
    }


@router.post("/fx/convert")
def convert_currency(
    from_currency: str,
    to_currency: str,
    amount: float,
    conversion_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Convert amount from one currency to another using historical rate
    
    Example: Convert 1000 USD to ZMW on Nov 5, 2025
    Query params:
    - from_currency=USD
    - to_currency=ZMW
    - amount=1000
    - conversion_date=2025-11-05
    """
    service = FXRevaluationService(db, current_user.company_id, current_user.id)
    
    from decimal import Decimal
    converted = service.convert_amount(
        amount=Decimal(str(amount)),
        from_currency=from_currency,
        to_currency=to_currency,
        conversion_date=conversion_date
    )
    
    if converted is None:
        raise HTTPException(
            status_code=404,
            detail=f"No exchange rate available for {from_currency}/{to_currency} on {conversion_date}"
        )
    
    rate = service.get_exchange_rate(from_currency, to_currency, conversion_date)
    
    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "amount": amount,
        "converted_amount": float(converted),
        "exchange_rate": rate,
        "conversion_date": conversion_date
    }


# ============================================================================
# SMART INVOICE ENDPOINTS (per Finance PDF spec - ZRA Compliance)
# ============================================================================


@router.post("/invoices/{invoice_id}/validate", response_model=schemas.InvoiceValidationResponse)
def validate_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Validate invoice for ZRA compliance
    
    Checks:
    - Supplier TPIN present
    - Customer TPIN present (for B2B)
    - Tax calculations correct
    - All required fields present
    - Invoice number unique
    """
    service = SmartInvoiceService(db, current_user.company_id, current_user.id)
    result = service.validate_invoice(invoice_id)
    return result


@router.get("/invoices/{invoice_id}/ubl")
def export_invoice_ubl(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Export invoice as UBL 2.1 XML (ZRA compliant)
    
    UBL (Universal Business Language) is the international standard
    for electronic invoicing and is required for ZRA e-invoice submission.
    
    Returns XML content with proper content type.
    """
    service = SmartInvoiceService(db, current_user.company_id, current_user.id)
    
    try:
        ubl_xml = service.generate_ubl_xml(invoice_id)
        
        # Return XML with proper content type
        return Response(
            content=ubl_xml,
            media_type="application/xml",
            headers={
                "Content-Disposition": f"attachment; filename=invoice_{invoice_id}.xml"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate UBL: {str(e)}")


@router.get("/invoices/{invoice_id}/json")
def export_invoice_json(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Export invoice as JSON (ZRA compliant)
    
    JSON format is an alternative to UBL XML for e-invoice submission.
    It contains all the same information in a more compact format.
    """
    service = SmartInvoiceService(db, current_user.company_id, current_user.id)
    
    try:
        json_invoice = service.generate_json_invoice(invoice_id)
        return json_invoice
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate JSON: {str(e)}")


@router.get("/invoices/{invoice_id}/qr")
def generate_invoice_qr_code(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Generate QR code for invoice (ZRA compliance)
    
    QR code contains:
    - Invoice number
    - Invoice date
    - Supplier TPIN
    - Total amount
    - Validation hash
    
    The QR code can be printed on the invoice for mobile verification.
    Returns PNG image.
    """
    service = SmartInvoiceService(db, current_user.company_id, current_user.id)
    
    try:
        qr_bytes = service.generate_qr_code(invoice_id)
        
        # Return image with proper content type
        return Response(
            content=qr_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=invoice_{invoice_id}_qr.png"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")


@router.post("/invoices/{invoice_id}/submit-zra")
def submit_invoice_to_zra(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Submit invoice to ZRA e-invoice system (placeholder)
    
    This endpoint will integrate with ZRA's Smart Invoice API
    to submit validated invoices for tax compliance.
    
    Note: Requires ZRA API credentials and active integration.
    """
    # Validate invoice first
    service = SmartInvoiceService(db, current_user.company_id, current_user.id)
    validation = service.validate_invoice(invoice_id)
    
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invoice validation failed",
                "errors": validation["errors"],
                "warnings": validation["warnings"]
            }
        )
    
    # TODO: Integrate with ZRA Smart Invoice API
    # This would involve:
    # 1. Generate UBL XML
    # 2. Sign XML with digital certificate
    # 3. Submit to ZRA endpoint
    # 4. Receive ZRA reference number
    # 5. Update invoice with ZRA status
    
    return {
        "success": True,
        "message": "ZRA integration pending - invoice validated and ready for submission",
        "invoice_id": invoice_id,
        "validation": validation,
        "next_steps": [
            "Configure ZRA API credentials",
            "Obtain digital signing certificate",
            "Enable ZRA integration in settings"
        ]
    }


# ============================================================================
# PAYMENT MATCHING ENDPOINTS (per Finance PDF spec)
# ============================================================================


@router.post("/payments/{payment_id}/match")
def match_payment_auto(
    payment_id: str,
    data: schemas.PaymentMatchRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Automatically match a payment to invoices/bills
    
    Matching logic:
    1. Exact match by reference number + amount
    2. High confidence: reference OR (amount + customer/supplier)
    3. Medium confidence: amount + date proximity
    4. Low confidence: customer/supplier only
    
    Returns:
    - Auto-matched if exact/high confidence
    - Suggestions for manual matching if medium/low confidence
    
    Example (match customer payment):
    {
      "payment_id": "pay_12345",
      "payment_type": "customer"
    }
    """
    service = PaymentMatchingEngine(db, current_user.company_id, current_user.id)
    result = service.match_payment_auto(
        payment_id=payment_id,
        payment_type=data.payment_type
    )
    return result


@router.post("/payments/{payment_id}/apply")
def apply_payment_manual(
    payment_id: str,
    invoice_id: Optional[str] = None,
    bill_id: Optional[str] = None,
    amount: float = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Manually apply payment to specific invoice/bill
    
    Use when automatic matching doesn't find the right match
    or when you want to override automatic suggestions.
    
    Query params:
    - invoice_id: ID of invoice to apply to (for customer payments)
    - bill_id: ID of bill to apply to (for supplier payments)
    - amount: Amount to apply (optional, defaults to full payment)
    
    Example: /payments/pay_123/apply?invoice_id=inv_456&amount=1000
    """
    service = PaymentMatchingEngine(db, current_user.company_id, current_user.id)
    
    from decimal import Decimal
    
    if invoice_id:
        result = service.apply_payment_to_invoice(
            payment_id=payment_id,
            invoice_id=invoice_id,
            amount=Decimal(str(amount)) if amount else None
        )
    elif bill_id:
        result = service.apply_payment_to_bill(
            payment_id=payment_id,
            bill_id=bill_id,
            amount=Decimal(str(amount)) if amount else None
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either invoice_id or bill_id must be provided"
        )
    
    return {
        "success": True,
        "payment_id": payment_id,
        "application": result
    }


@router.post("/payments/{payment_id}/split", response_model=dict)
def split_payment(
    payment_id: str,
    data: schemas.PaymentSplitRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Split a payment across multiple invoices/bills
    
    Use when one payment covers multiple invoices/bills.
    
    Example (split 5000 payment across 3 invoices):
    {
      "payment_id": "pay_123",
      "allocations": [
        {"invoice_id": "inv_001", "amount": 2000},
        {"invoice_id": "inv_002", "amount": 1500},
        {"invoice_id": "inv_003", "amount": 1500}
      ],
      "payment_type": "customer"
    }
    """
    service = PaymentMatchingEngine(db, current_user.company_id, current_user.id)
    
    result = service.apply_payment_split(
        payment_id=payment_id,
        allocations=[a.dict() for a in data.allocations],
        payment_type=data.payment_type
    )
    
    return result


@router.get("/payments/unmatched")
def get_unmatched_payments(
    payment_type: str = "customer",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get list of unmatched payments requiring manual attention
    
    Query params:
    - payment_type: "customer" or "supplier"
    
    Returns payments that haven't been matched to any invoices/bills.
    These require manual review and matching.
    """
    service = PaymentMatchingEngine(db, current_user.company_id, current_user.id)
    
    unmatched = service.get_unmatched_payments(payment_type=payment_type)
    
    return {
        "success": True,
        "count": len(unmatched),
        "payments": unmatched
    }


# ============================================================================
# FIXED ASSET DEPRECIATION ENDPOINTS (per Finance PDF spec)
# ============================================================================


@router.post("/assets", response_model=schemas.FixedAssetResponse)
def create_fixed_asset(
    data: schemas.FixedAssetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new fixed asset
    
    Example (purchase a vehicle):
    {
      "asset_name": "Toyota Hilux 2025",
      "asset_code": "VEH-001",
      "asset_category": "Vehicle",
      "purchase_date": "2025-01-15",
      "purchase_cost": 450000,
      "salvage_value": 50000,
      "useful_life_years": 5,
      "depreciation_method": "declining_balance",
      "location": "Head Office",
      "serial_number": "VIN123456789"
    }
    """
    service = FixedAssetDepreciationService(db, current_user.company_id, current_user.id)
    
    from decimal import Decimal
    asset = service.create_fixed_asset(
        asset_name=data.asset_name,
        asset_code=data.asset_code,
        asset_category=data.asset_category,
        purchase_date=data.purchase_date,
        purchase_cost=Decimal(str(data.purchase_cost)),
        salvage_value=Decimal(str(data.salvage_value)),
        useful_life_years=data.useful_life_years,
        depreciation_method=data.depreciation_method,
        account_id=data.account_id,
        location=data.location,
        serial_number=data.serial_number,
        supplier_id=data.supplier_id
    )
    
    return asset


@router.get("/assets", response_model=List[schemas.FixedAssetResponse])
def list_fixed_assets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    List all fixed assets
    
    Query params:
    - status: Filter by status (active, disposed, fully_depreciated)
    - category: Filter by category (Building, Vehicle, Equipment, etc.)
    """
    query = db.query(models.FixedAsset).filter(
        models.FixedAsset.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.FixedAsset.status == status)
    if category:
        query = query.filter(models.FixedAsset.asset_category == category)
    
    assets = query.order_by(models.FixedAsset.asset_code).all()
    return assets


@router.get("/assets/{asset_id}", response_model=schemas.FixedAssetResponse)
def get_fixed_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get details of a specific fixed asset"""
    asset = db.query(models.FixedAsset).filter(
        models.FixedAsset.id == asset_id,
        models.FixedAsset.company_id == current_user.company_id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed asset not found")
    
    return asset


@router.get("/assets/{asset_id}/schedule", response_model=List[schemas.DepreciationScheduleEntry])
def get_depreciation_schedule(
    asset_id: str,
    num_periods: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get depreciation schedule for an asset
    
    Shows projected depreciation for each period.
    
    Query params:
    - num_periods: Number of periods to show (default: until fully depreciated)
    """
    service = FixedAssetDepreciationService(db, current_user.company_id, current_user.id)
    
    schedule = service.generate_depreciation_schedule(
        asset_id=asset_id,
        num_periods=num_periods
    )
    
    return schedule


@router.post("/assets/{asset_id}/depreciate")
def record_asset_depreciation(
    asset_id: str,
    period_date: date,
    create_journal: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Record depreciation for a specific asset for a period
    
    This updates accumulated depreciation and optionally creates a journal entry.
    
    Query params:
    - period_date: Period to record depreciation for (YYYY-MM-DD)
    - create_journal: Create depreciation journal entry (default: true)
    
    Example: /assets/asset_123/depreciate?period_date=2025-01-31&create_journal=true
    """
    service = FixedAssetDepreciationService(db, current_user.company_id, current_user.id)
    
    result = service.record_depreciation(
        asset_id=asset_id,
        period_date=period_date,
        create_journal=create_journal
    )
    
    return result


@router.post("/assets/depreciate/batch")
def run_monthly_depreciation(
    period_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Run depreciation for ALL active assets for a specific month
    
    This is typically run as a scheduled job at month-end.
    It processes all active assets and creates depreciation journals.
    
    Query params:
    - period_date: Period to run depreciation for (YYYY-MM-DD)
    
    Example: /assets/depreciate/batch?period_date=2025-01-31
    """
    service = FixedAssetDepreciationService(db, current_user.company_id, current_user.id)
    
    result = service.run_monthly_depreciation(period_date=period_date)
    
    return result


@router.post("/assets/{asset_id}/dispose")
def dispose_fixed_asset(
    asset_id: str,
    data: schemas.AssetDisposalRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Dispose of a fixed asset
    
    Calculates gain/loss on disposal and optionally creates journal entry.
    
    Example (sell vehicle for 150K):
    {
      "disposal_date": "2025-11-05",
      "disposal_proceeds": 150000,
      "create_journal": true
    }
    """
    service = FixedAssetDepreciationService(db, current_user.company_id, current_user.id)
    
    from decimal import Decimal
    result = service.dispose_asset(
        asset_id=asset_id,
        disposal_date=data.disposal_date,
        disposal_proceeds=Decimal(str(data.disposal_proceeds)),
        create_journal=data.create_journal
    )
    
    return result


# ============================================================================
# INTERCOMPANY TRANSACTION ENDPOINTS (per Finance PDF spec)
# ============================================================================


@router.post("/intercompany/sale")
def record_intercompany_sale(
    data: schemas.IntercompanySaleRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Record an intercompany sale between entities
    
    Creates matching journal entries in both companies:
    - Seller: DR Intercompany Receivable / CR Intercompany Sales
    - Buyer: DR Intercompany Purchases / CR Intercompany Payable
    
    Example (Company A sells to Company B for 50,000):
    {
      "from_company_id": "company_a_id",
      "to_company_id": "company_b_id",
      "transaction_date": "2025-11-05",
      "amount": 50000,
      "description": "Management services",
      "reference": "IC-2025-001"
    }
    """
    service = IntercompanyTransactionService(db, current_user.company_id, current_user.id)
    
    from decimal import Decimal
    result = service.record_intercompany_sale(
        from_company_id=data.from_company_id,
        to_company_id=data.to_company_id,
        transaction_date=data.transaction_date,
        amount=Decimal(str(data.amount)),
        description=data.description,
        reference=data.reference
    )
    
    return result


@router.post("/intercompany/loan")
def record_intercompany_loan(
    data: schemas.IntercompanyLoanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Record an intercompany loan between entities
    
    Creates matching journal entries in both companies:
    - Lender: DR Intercompany Loan Receivable / CR Cash
    - Borrower: DR Cash / CR Intercompany Loan Payable
    
    Example (Company A lends 100,000 to Company B):
    {
      "lender_company_id": "company_a_id",
      "borrower_company_id": "company_b_id",
      "loan_date": "2025-11-05",
      "loan_amount": 100000,
      "interest_rate": 8.5,
      "maturity_date": "2026-11-05",
      "description": "Working capital loan",
      "reference": "LOAN-2025-001"
    }
    """
    service = IntercompanyTransactionService(db, current_user.company_id, current_user.id)
    
    from decimal import Decimal
    result = service.record_intercompany_loan(
        lender_company_id=data.lender_company_id,
        borrower_company_id=data.borrower_company_id,
        loan_date=data.loan_date,
        loan_amount=Decimal(str(data.loan_amount)),
        interest_rate=data.interest_rate,
        maturity_date=data.maturity_date,
        description=data.description,
        reference=data.reference
    )
    
    return result


@router.post("/intercompany/eliminations")
def generate_elimination_entries(
    data: schemas.EliminationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Generate elimination entries for consolidated reporting
    
    Eliminates intercompany balances:
    - Intercompany receivables vs. payables
    - Intercompany sales vs. purchases
    - Intercompany loans
    - Unrealized profit on inventory
    
    Run this at period-end for consolidation.
    
    Example (eliminate all IC transactions as of Jan 31, 2025):
    {
      "period_end_date": "2025-01-31",
      "company_ids": ["company_a_id", "company_b_id", "company_c_id"]
    }
    """
    service = IntercompanyTransactionService(db, current_user.company_id, current_user.id)
    
    result = service.generate_elimination_entries(
        period_end_date=data.period_end_date,
        company_ids=data.company_ids
    )
    
    return result


@router.get("/intercompany/balances")
def get_intercompany_balances(
    as_of_date: date,
    company_ids: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get intercompany balances between entities
    
    Shows:
    - Intercompany receivables
    - Intercompany payables
    - Intercompany loans
    - Net position by company
    
    Query params:
    - as_of_date: Date to get balances as of (YYYY-MM-DD)
    - company_ids: Comma-separated list of company IDs (optional)
    
    Example: /intercompany/balances?as_of_date=2025-01-31&company_ids=comp1,comp2
    """
    service = IntercompanyTransactionService(db, current_user.company_id, current_user.id)
    
    # Parse company_ids if provided
    company_list = company_ids.split(",") if company_ids else None
    
    balances = service.get_intercompany_balances(
        as_of_date=as_of_date,
        company_ids=company_list
    )
    
    return balances


@router.post("/intercompany/reconcile")
def reconcile_intercompany_accounts(
    data: schemas.ReconciliationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Reconcile intercompany accounts between two entities
    
    Identifies:
    - Matched transactions
    - Unmatched transactions
    - Amount discrepancies
    - Balance differences
    
    Example (reconcile Company A with Company B):
    {
      "company1_id": "company_a_id",
      "company2_id": "company_b_id",
      "as_of_date": "2025-01-31"
    }
    """
    service = IntercompanyTransactionService(db, current_user.company_id, current_user.id)
    
    result = service.reconcile_intercompany_accounts(
        company1_id=data.company1_id,
        company2_id=data.company2_id,
        as_of_date=data.as_of_date
    )
    
    return result


# ============================================================================
# FINANCIAL REPORTS ENDPOINTS (per Finance PDF spec)
# ============================================================================


@router.get("/reports/balance-sheet")
def get_balance_sheet_report(
    as_of_date: date,
    comparison_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Generate Balance Sheet (Statement of Financial Position)
    
    Shows:
    - Assets (Current + Non-Current)
    - Liabilities (Current + Non-Current)
    - Equity
    - Verification: Assets = Liabilities + Equity
    
    Query params:
    - as_of_date: Date to generate balance sheet as of (YYYY-MM-DD)
    - comparison_date: Optional prior date for comparison
    
    Example: /reports/balance-sheet?as_of_date=2025-01-31
    """
    service = FinancialReportService(db, current_user.company_id, current_user.id)
    
    report = service.get_balance_sheet(
        as_of_date=as_of_date,
        comparison_date=comparison_date
    )
    
    return report


@router.get("/reports/income-statement")
def get_income_statement_report(
    start_date: date,
    end_date: date,
    comparison_start: Optional[date] = None,
    comparison_end: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Generate Income Statement (Profit & Loss)
    
    Shows:
    - Revenue (all revenue accounts)
    - Expenses (all expense accounts)
    - Net Income (Revenue - Expenses)
    - Profit Margin %
    
    Query params:
    - start_date: Period start date (YYYY-MM-DD)
    - end_date: Period end date (YYYY-MM-DD)
    - comparison_start: Optional comparison period start
    - comparison_end: Optional comparison period end
    
    Example: /reports/income-statement?start_date=2025-01-01&end_date=2025-01-31
    """
    service = FinancialReportService(db, current_user.company_id, current_user.id)
    
    report = service.get_income_statement(
        start_date=start_date,
        end_date=end_date,
        comparison_start=comparison_start,
        comparison_end=comparison_end
    )
    
    return report


@router.get("/reports/trial-balance")
def get_trial_balance_report(
    as_of_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Generate Trial Balance
    
    Shows all accounts with their debit and credit balances
    Verifies that total debits = total credits
    
    Essential for:
    - Period-end verification
    - Finding posting errors
    - Balance sheet preparation
    
    Query params:
    - as_of_date: Date to generate trial balance as of (YYYY-MM-DD)
    
    Example: /reports/trial-balance?as_of_date=2025-01-31
    """
    service = FinancialReportService(db, current_user.company_id, current_user.id)
    
    report = service.get_trial_balance(as_of_date=as_of_date)
    
    return report


@router.get("/reports/general-ledger")
def get_general_ledger_report(
    start_date: date,
    end_date: date,
    account_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Generate General Ledger Report
    
    Shows all journal entries for a period, grouped by account
    Optionally filtered by a specific account
    
    Each account shows:
    - All transactions
    - Total debits
    - Total credits
    - Net balance
    
    Query params:
    - start_date: Period start date (YYYY-MM-DD)
    - end_date: Period end date (YYYY-MM-DD)
    - account_id: Optional account filter
    
    Example: /reports/general-ledger?start_date=2025-01-01&end_date=2025-01-31
    Example: /reports/general-ledger?start_date=2025-01-01&end_date=2025-01-31&account_id=acc123
    """
    service = FinancialReportService(db, current_user.company_id, current_user.id)
    
    report = service.get_general_ledger(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id
    )
    
    return report


@router.get("/reports/account-activity/{account_id}")
def get_account_activity_report(
    account_id: str,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get detailed activity for a specific account (drill-down)
    
    Shows:
    - Opening balance
    - All transactions in period with running balance
    - Closing balance
    - Net change
    - Direct links to journal entries for drill-down
    
    This is the drill-down endpoint - click an account in any report
    to see detailed transactions.
    
    Query params:
    - start_date: Period start date (YYYY-MM-DD)
    - end_date: Period end date (YYYY-MM-DD)
    
    Example: /reports/account-activity/acc123?start_date=2025-01-01&end_date=2025-01-31
    """
    service = FinancialReportService(db, current_user.company_id, current_user.id)
    
    report = service.get_account_activity(
        account_id=account_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return report


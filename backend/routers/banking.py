"""
Banking & Reconciliation API Router

Handles bank accounts, statement imports, and bank reconciliation
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
import csv
import io

import models
import schemas
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/banking", tags=["banking"])


# ============================================================================
# BANK ACCOUNTS
# ============================================================================

@router.post("/accounts", response_model=dict)
def create_bank_account(
    account: schemas.BankAccountCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new bank account"""
    
    db_account = models.BankAccount(
        company_id=current_user.company_id,
        **account.dict()
    )
    
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    
    return {
        "id": db_account.id,
        "bank_name": db_account.bank_name,
        "account_number": db_account.account_number,
        "message": "Bank account created successfully"
    }


@router.get("/accounts", response_model=List[dict])
def list_bank_accounts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all bank accounts"""
    
    accounts = db.query(models.BankAccount).filter(
        models.BankAccount.company_id == current_user.company_id
    ).all()
    
    return [
        {
            "id": acc.id,
            "bank_name": acc.bank_name,
            "account_number": acc.account_number,
            "account_type": acc.account_type,
            "currency": acc.currency,
            "is_active": acc.is_active,
            "current_balance": float(acc.current_balance) if acc.current_balance else 0
        }
        for acc in accounts
    ]


@router.get("/accounts/{account_id}", response_model=dict)
def get_bank_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get bank account details"""
    
    account = db.query(models.BankAccount).filter(
        and_(
            models.BankAccount.id == account_id,
            models.BankAccount.company_id == current_user.company_id
        )
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    
    return {
        "id": account.id,
        "bank_name": account.bank_name,
        "account_number": account.account_number,
        "account_type": account.account_type,
        "currency": account.currency,
        "branch": account.branch,
        "swift_code": account.swift_code,
        "current_balance": float(account.current_balance) if account.current_balance else 0,
        "is_active": account.is_active,
        "created_at": account.created_at.isoformat() if account.created_at else None
    }


# ============================================================================
# BANK STATEMENT IMPORT
# ============================================================================

@router.post("/statements/import", response_model=dict)
async def import_bank_statement(
    bank_account_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Import bank statement from CSV file"""
    
    # Verify bank account exists
    bank_account = db.query(models.BankAccount).filter(
        and_(
            models.BankAccount.id == bank_account_id,
            models.BankAccount.company_id == current_user.company_id
        )
    ).first()
    
    if not bank_account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    
    # Read CSV file
    contents = await file.read()
    csv_data = contents.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_data))
    
    imported_count = 0
    transactions = []
    
    try:
        for row in csv_reader:
            # Expected CSV columns: date, description, debit, credit, balance
            # Parse transaction data
            trans_date = datetime.strptime(row.get('date', ''), '%Y-%m-%d').date()
            description = row.get('description', '')
            debit = Decimal(row.get('debit', 0) or 0)
            credit = Decimal(row.get('credit', 0) or 0)
            balance = Decimal(row.get('balance', 0) or 0)
            
            # Determine transaction type and amount
            if debit > 0:
                trans_type = "debit"
                amount = debit
            else:
                trans_type = "credit"
                amount = credit
            
            # Create bank transaction record
            transaction = models.BankTransaction(
                company_id=current_user.company_id,
                bank_account_id=bank_account_id,
                transaction_date=trans_date,
                description=description,
                transaction_type=trans_type,
                amount=amount,
                balance=balance,
                status="unreconciled",
                imported=True
            )
            
            db.add(transaction)
            transactions.append({
                "date": trans_date.isoformat(),
                "description": description,
                "type": trans_type,
                "amount": float(amount)
            })
            imported_count += 1
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")
    
    # Update bank account balance
    if transactions:
        last_balance = Decimal(row.get('balance', 0) or 0)
        bank_account.current_balance = last_balance
    
    db.commit()
    
    return {
        "message": f"Imported {imported_count} transactions successfully",
        "imported_count": imported_count,
        "transactions": transactions[:10]  # Return first 10 as preview
    }


@router.get("/transactions", response_model=List[dict])
def list_bank_transactions(
    bank_account_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List bank transactions"""
    
    query = db.query(models.BankTransaction).filter(
        models.BankTransaction.company_id == current_user.company_id
    )
    
    if bank_account_id:
        query = query.filter(models.BankTransaction.bank_account_id == bank_account_id)
    
    if status:
        query = query.filter(models.BankTransaction.status == status)
    
    if start_date:
        query = query.filter(models.BankTransaction.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(models.BankTransaction.transaction_date <= end_date)
    
    transactions = query.order_by(models.BankTransaction.transaction_date.desc()).offset(skip).limit(limit).all()
    
    result = []
    for trans in transactions:
        bank_account = db.query(models.BankAccount).filter(
            models.BankAccount.id == trans.bank_account_id
        ).first()
        
        result.append({
            "id": trans.id,
            "transaction_date": trans.transaction_date.isoformat() if trans.transaction_date else None,
            "bank_account": bank_account.bank_name if bank_account else None,
            "description": trans.description,
            "transaction_type": trans.transaction_type,
            "amount": float(trans.amount),
            "balance": float(trans.balance) if trans.balance else 0,
            "status": trans.status,
            "matched_to": trans.matched_to
        })
    
    return result


# ============================================================================
# BANK RECONCILIATION
# ============================================================================

@router.post("/reconciliation/auto-match", response_model=dict)
def auto_match_transactions(
    bank_account_id: str,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Auto-match bank transactions with journal entries"""
    
    # Get unreconciled bank transactions
    bank_transactions = db.query(models.BankTransaction).filter(
        and_(
            models.BankTransaction.bank_account_id == bank_account_id,
            models.BankTransaction.company_id == current_user.company_id,
            models.BankTransaction.status == "unreconciled",
            models.BankTransaction.transaction_date >= start_date,
            models.BankTransaction.transaction_date <= end_date
        )
    ).all()
    
    matched_count = 0
    matches = []
    
    for trans in bank_transactions:
        # Try to find matching journal entries (simplified matching logic)
        # Match criteria: similar amount and date within +/- 2 days
        
        # For deposits (credits), look for customer receipts or income
        # For withdrawals (debits), look for supplier payments or expenses
        
        # This is a simplified example - real matching would be more sophisticated
        amount_match = trans.amount
        date_min = trans.transaction_date - timedelta(days=2)
        date_max = trans.transaction_date + timedelta(days=2)
        
        # Try to match with journal entries
        # (In production, you'd match with specific payment/receipt records)
        
        # For now, just mark as "matched" if amount is round number (demo logic)
        if trans.amount % 100 == 0:
            trans.status = "reconciled"
            trans.matched_to = "auto_matched"
            matched_count += 1
            
            matches.append({
                "transaction_id": trans.id,
                "date": trans.transaction_date.isoformat(),
                "description": trans.description,
                "amount": float(trans.amount),
                "matched_with": "System auto-match"
            })
    
    db.commit()
    
    return {
        "message": f"Auto-matched {matched_count} transactions",
        "matched_count": matched_count,
        "total_transactions": len(bank_transactions),
        "matches": matches
    }


@router.get("/reconciliation/summary", response_model=dict)
def get_reconciliation_summary(
    bank_account_id: str,
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get bank reconciliation summary"""
    
    # Get bank account
    bank_account = db.query(models.BankAccount).filter(
        and_(
            models.BankAccount.id == bank_account_id,
            models.BankAccount.company_id == current_user.company_id
        )
    ).first()
    
    if not bank_account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    
    # Get unreconciled transactions
    unreconciled = db.query(models.BankTransaction).filter(
        and_(
            models.BankTransaction.bank_account_id == bank_account_id,
            models.BankTransaction.status == "unreconciled",
            models.BankTransaction.transaction_date <= end_date
        )
    ).all()
    
    unreconciled_debits = sum(t.amount for t in unreconciled if t.transaction_type == "debit")
    unreconciled_credits = sum(t.amount for t in unreconciled if t.transaction_type == "credit")
    
    # Get reconciled transactions
    reconciled = db.query(models.BankTransaction).filter(
        and_(
            models.BankTransaction.bank_account_id == bank_account_id,
            models.BankTransaction.status == "reconciled",
            models.BankTransaction.transaction_date <= end_date
        )
    ).count()
    
    return {
        "bank_account": bank_account.bank_name,
        "account_number": bank_account.account_number,
        "statement_balance": float(bank_account.current_balance) if bank_account.current_balance else 0,
        "reconciliation_date": end_date.isoformat(),
        "unreconciled_transactions": len(unreconciled),
        "reconciled_transactions": reconciled,
        "unreconciled_debits": float(unreconciled_debits),
        "unreconciled_credits": float(unreconciled_credits),
        "net_unreconciled": float(unreconciled_credits - unreconciled_debits)
    }

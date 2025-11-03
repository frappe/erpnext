from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date
import models
import schemas
from database import get_db
from auth import get_current_user
from services.banking.bank_factory import BankIntegrationFactory
from services.banking.bank_sync_service import BankSyncService
from cryptography.fernet import Fernet
import os

# Initialize encryption - In production, use KMS or vault
ENCRYPTION_KEY = os.environ.get("BANK_CREDENTIALS_KEY", Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY if isinstance(ENCRYPTION_KEY, bytes) else ENCRYPTION_KEY.encode())

router = APIRouter(prefix="/api/banking", tags=["Banking"])

@router.get("/supported-banks")
async def get_supported_banks():
    """Get list of all supported banks"""
    return {
        "banks": BankIntegrationFactory.get_supported_banks()
    }

@router.post("/connections")
async def create_bank_connection(
    connection_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new bank connection
    
    Required fields:
    - provider_code: str (zanaco, absa, stanbic, fnb, atlas_mara)
    - connection_name: str
    - bank_name: str
    - account_number: str
    - api_username: str
    - api_key: str
    - api_secret: str
    - api_endpoint: str
    """
    # Properly encrypt API credentials using Fernet
    encrypted_key = cipher_suite.encrypt(connection_data["api_key"].encode()).decode()
    encrypted_secret = cipher_suite.encrypt(connection_data.get("api_secret", "").encode()).decode()
    
    # Create bank connection
    connection = models.BankConnection(
        company_id=current_user.company_id,
        connection_name=connection_data["connection_name"],
        bank_name=connection_data["bank_name"],
        provider_code=connection_data["provider_code"],
        account_number=connection_data["account_number"],
        api_username=connection_data["api_username"],
        api_key_encrypted=encrypted_key,
        api_secret_encrypted=encrypted_secret,
        api_endpoint=connection_data.get("api_endpoint", f"https://api.{connection_data['provider_code']}.co.zm"),
        connection_type=connection_data.get("connection_type", "api"),
        status="pending",
        created_by=current_user.id
    )
    
    db.add(connection)
    db.commit()
    db.refresh(connection)
    
    return {
        "id": connection.id,
        "connection_name": connection.connection_name,
        "bank_name": connection.bank_name,
        "provider_code": connection.provider_code,
        "account_number": connection.account_number,
        "status": connection.status,
        "connection_type": connection.connection_type
    }

@router.get("/connections")
async def list_bank_connections(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all bank connections for the current company - returns array directly"""
    connections = db.query(models.BankConnection).filter(
        models.BankConnection.company_id == current_user.company_id
    ).all()
    
    return [
        {
            "id": conn.id,
            "connection_name": conn.connection_name or f"{conn.bank_name} - {conn.account_number}",
            "bank_name": conn.bank_name,
            "provider_code": conn.provider_code or conn.bank_code,
            "account_number": conn.account_number,
            "connection_type": conn.connection_type or "api",
            "status": conn.status or "pending",
            "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None
        }
        for conn in connections
    ]

@router.post("/connections/{connection_id}/test")
async def test_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Test a bank connection"""
    # Verify company ownership
    connection = db.query(models.BankConnection).filter(
        models.BankConnection.id == connection_id,
        models.BankConnection.company_id == current_user.company_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    
    # Test connection
    sync_service = BankSyncService(db)
    result = await sync_service.test_bank_connection(connection_id)
    
    return result

@router.post("/connections/{connection_id}/sync")
async def sync_transactions(
    connection_id: int,
    sync_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Sync transactions from bank"""
    # Verify company ownership
    connection = db.query(models.BankConnection).filter(
        models.BankConnection.id == connection_id,
        models.BankConnection.company_id == current_user.company_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    
    # Sync transactions
    from datetime import datetime
    sync_service = BankSyncService(db)
    from_date = datetime.fromisoformat(sync_data["from_date"]) if "from_date" in sync_data else None
    to_date = datetime.fromisoformat(sync_data["to_date"]) if "to_date" in sync_data else None
    
    result = await sync_service.sync_bank_transactions(
        bank_connection_id=connection_id,
        from_date=from_date,
        to_date=to_date,
        triggered_by=current_user.id
    )
    
    return result

@router.get("/connections/{connection_id}/transactions")
async def get_bank_transactions(
    connection_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get synced bank transactions for a connection"""
    # Verify company ownership
    connection = db.query(models.BankConnection).filter(
        models.BankConnection.id == connection_id,
        models.BankConnection.company_id == current_user.company_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    
    # Get transactions - return bare array
    transactions = db.query(models.BankTransaction).filter(
        models.BankTransaction.bank_connection_id == connection_id
    ).order_by(models.BankTransaction.transaction_date.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": txn.id,
            "transaction_id": txn.bank_transaction_id,
            "transaction_date": txn.transaction_date,
            "description": txn.description,
            "amount": txn.amount,
            "transaction_type": txn.transaction_type,
            "balance_after": txn.balance_after,
            "reference_number": txn.reference_number,
            "counterparty_name": txn.counterparty_name,
            "is_reconciled": txn.is_reconciled
        }
        for txn in transactions
    ]

@router.put("/connections/{connection_id}")
async def update_bank_connection(
    connection_id: int,
    update_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update bank connection settings"""
    connection = db.query(models.BankConnection).filter(
        models.BankConnection.id == connection_id,
        models.BankConnection.company_id == current_user.company_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    
    # Update allowed fields
    if "auto_sync_enabled" in update_data:
        connection.auto_sync_enabled = update_data["auto_sync_enabled"]
    if "sync_frequency" in update_data:
        connection.sync_frequency = update_data["sync_frequency"]
    if "is_active" in update_data:
        connection.is_active = update_data["is_active"]
    
    db.commit()
    
    return {"message": "Bank connection updated successfully"}

@router.delete("/connections/{connection_id}")
async def delete_bank_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete/deactivate a bank connection"""
    connection = db.query(models.BankConnection).filter(
        models.BankConnection.id == connection_id,
        models.BankConnection.company_id == current_user.company_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    
    # Soft delete - just mark as inactive
    connection.is_active = False
    db.commit()
    
    return {"message": "Bank connection deactivated successfully"}

@router.get("/transactions")
async def get_all_transactions(
    posting_status: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all external transactions - returns array directly"""
    query = db.query(models.ExternalTransaction).filter(
        models.ExternalTransaction.company_id == current_user.company_id
    )
    
    if posting_status:
        query = query.filter(models.ExternalTransaction.posting_status == posting_status)
    
    transactions = query.order_by(models.ExternalTransaction.transaction_date.desc()).limit(100).all()
    
    return [
        {
            "id": txn.id,
            "transaction_date": txn.transaction_date.isoformat() if txn.transaction_date else None,
            "description": txn.description,
            "counterparty_name": txn.counterparty_name,
            "reference_number": txn.reference_number,
            "amount": float(txn.amount) if txn.amount else 0,
            "currency": txn.currency or "ZMW",
            "direction": txn.direction,
            "posting_status": txn.posting_status or "pending"
        }
        for txn in transactions
    ]

@router.get("/connections/{connection_id}/reconciliation-report")
async def get_reconciliation_report(
    connection_id: int,
    as_of_date: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get reconciliation report for a bank connection"""
    from datetime import datetime
    from services.banking.reconciliation_engine import AIReconciliationEngine
    
    engine = AIReconciliationEngine(db, current_user.company_id, current_user.id)
    report_date = datetime.fromisoformat(as_of_date) if as_of_date else datetime.utcnow()
    
    report = await engine.get_reconciliation_report(connection_id, report_date)
    return report

@router.post("/connections/{connection_id}/reconcile")
async def reconcile_bank_account(
    connection_id: int,
    reconcile_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Run AI-driven reconciliation"""
    from datetime import datetime
    from services.banking.reconciliation_engine import AIReconciliationEngine
    
    engine = AIReconciliationEngine(db, current_user.company_id, current_user.id)
    
    from_date = datetime.fromisoformat(reconcile_data["from_date"])
    to_date = datetime.fromisoformat(reconcile_data["to_date"])
    auto_match = reconcile_data.get("auto_match", True)
    
    result = await engine.reconcile_bank_account(connection_id, from_date, to_date, auto_match)
    return result

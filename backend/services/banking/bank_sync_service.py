from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
import models
from .bank_factory import BankIntegrationFactory
from .base_bank_integration import BankTransaction

class BankSyncService:
    """
    Service for syncing bank transactions and managing bank connections
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def sync_bank_transactions(
        self,
        bank_connection_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        triggered_by: Optional[str] = None
    ) -> dict:
        """
        Sync transactions from bank API for a given connection
        
        Returns:
            Dictionary with sync results
        """
        # Get bank connection
        connection = self.db.query(models.BankConnection).filter(
            models.BankConnection.id == bank_connection_id
        ).first()
        
        if not connection:
            raise ValueError(f"Bank connection {bank_connection_id} not found")
        
        # Set default date range if not provided (last 30 days)
        if not from_date:
            from_date = date.today() - timedelta(days=30)
        if not to_date:
            to_date = date.today()
        
        # Create sync history record
        sync_history = models.BankSyncHistory(
            company_id=connection.company_id,
            bank_connection_id=bank_connection_id,
            sync_type="manual" if triggered_by else "auto",
            from_date=from_date,
            to_date=to_date,
            triggered_by=triggered_by
        )
        self.db.add(sync_history)
        self.db.commit()
        
        try:
            # Decrypt API credentials (in production, use proper encryption)
            api_key = self._decrypt_key(connection.api_key_encrypted)
            
            # Create bank integration instance
            bank_integration = BankIntegrationFactory.create(
                bank_code=connection.bank_code,
                api_username=connection.api_username,
                api_key=api_key,
                api_endpoint=connection.api_endpoint
            )
            
            # Fetch transactions from bank
            transactions = await bank_integration.fetch_transactions(
                account_number=connection.account_number,
                from_date=from_date,
                to_date=to_date
            )
            
            # Store transactions in database
            new_count = 0
            updated_count = 0
            failed_count = 0
            
            for txn in transactions:
                try:
                    # Check if transaction already exists
                    existing = self.db.query(models.BankTransaction).filter(
                        models.BankTransaction.bank_connection_id == bank_connection_id,
                        models.BankTransaction.bank_transaction_id == txn.transaction_id
                    ).first()
                    
                    if existing:
                        # Update existing transaction
                        existing.description = txn.description
                        existing.balance_after = txn.balance_after
                        updated_count += 1
                    else:
                        # Create new transaction
                        new_txn = models.BankTransaction(
                            company_id=connection.company_id,
                            bank_connection_id=bank_connection_id,
                            bank_transaction_id=txn.transaction_id,
                            transaction_date=txn.transaction_date,
                            posting_date=txn.posting_date,
                            description=txn.description,
                            transaction_type=txn.transaction_type,
                            amount=txn.amount,
                            balance_after=txn.balance_after,
                            currency=txn.currency,
                            reference_number=txn.reference_number,
                            counterparty_name=txn.counterparty_name,
                            counterparty_account=txn.counterparty_account
                        )
                        self.db.add(new_txn)
                        new_count += 1
                
                except Exception as e:
                    failed_count += 1
                    print(f"Failed to save transaction {txn.transaction_id}: {str(e)}")
            
            # Commit all transactions
            self.db.commit()
            
            # Update sync history
            sync_history.status = "completed"
            sync_history.sync_completed_at = datetime.utcnow()
            sync_history.transactions_fetched = len(transactions)
            sync_history.transactions_new = new_count
            sync_history.transactions_updated = updated_count
            sync_history.transactions_failed = failed_count
            
            # Update connection last sync
            connection.last_sync_at = datetime.utcnow()
            connection.last_sync_status = "success"
            
            self.db.commit()
            
            return {
                "success": True,
                "total_fetched": len(transactions),
                "new": new_count,
                "updated": updated_count,
                "failed": failed_count,
                "sync_id": sync_history.id
            }
        
        except Exception as e:
            # Update sync history with error
            sync_history.status = "failed"
            sync_history.sync_completed_at = datetime.utcnow()
            sync_history.error_message = str(e)
            
            # Update connection status
            connection.last_sync_status = "failed"
            
            self.db.commit()
            
            return {
                "success": False,
                "error": str(e),
                "sync_id": sync_history.id
            }
    
    async def test_bank_connection(self, bank_connection_id: str) -> dict:
        """
        Test a bank connection to verify credentials and connectivity
        
        Returns:
            Connection status dictionary
        """
        connection = self.db.query(models.BankConnection).filter(
            models.BankConnection.id == bank_connection_id
        ).first()
        
        if not connection:
            raise ValueError(f"Bank connection {bank_connection_id} not found")
        
        try:
            api_key = self._decrypt_key(connection.api_key_encrypted)
            
            bank_integration = BankIntegrationFactory.create(
                bank_code=connection.bank_code,
                api_username=connection.api_username,
                api_key=api_key,
                api_endpoint=connection.api_endpoint
            )
            
            status = await bank_integration.test_connection()
            
            # Update connection status
            connection.connection_status = "connected" if status.is_connected else "failed"
            self.db.commit()
            
            return {
                "success": status.is_connected,
                "message": status.status_message,
                "details": status.error_details
            }
        
        except Exception as e:
            connection.connection_status = "failed"
            self.db.commit()
            
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    def _decrypt_key(self, encrypted_key: str) -> str:
        """
        Decrypt API key (placeholder - implement proper encryption in production)
        """
        import base64
        try:
            return base64.b64decode(encrypted_key.encode()).decode()
        except:
            return encrypted_key

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import models
import logging

logger = logging.getLogger(__name__)

class AutoPostingEngine:
    """
    Automated posting engine to convert bank and mobile money transactions
    into journal entries based on configurable posting rules.
    
    Flow: External Transaction → Match Posting Rule → Create Journal Entry → Post to GL/AR/AP
    """
    
    def __init__(self, db: Session, company_id: int, user_id: int):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
    
    async def process_external_transaction(
        self, 
        external_transaction_id: int
    ) -> Dict[str, Any]:
        """
        Process a single external transaction and generate journal entry
        """
        # Get external transaction
        ext_txn = self.db.query(models.ExternalTransaction).filter(
            models.ExternalTransaction.id == external_transaction_id,
            models.ExternalTransaction.company_id == self.company_id
        ).first()
        
        if not ext_txn:
            return {"success": False, "error": "External transaction not found"}
        
        if ext_txn.posting_status == "posted":
            return {"success": False, "error": "Transaction already posted"}
        
        # Find matching posting rule
        posting_rule = self._find_matching_rule(ext_txn)
        
        if not posting_rule:
            logger.warning(f"No matching posting rule for transaction {ext_txn.id}")
            return {
                "success": False, 
                "error": "No matching posting rule",
                "requires_manual_review": True
            }
        
        # Generate journal entry
        try:
            journal_entry = self._create_journal_entry(ext_txn, posting_rule)
            
            # Update external transaction status
            ext_txn.posting_status = "posted"
            ext_txn.journal_entry_id = journal_entry.id
            ext_txn.posted_at = datetime.utcnow()
            ext_txn.posted_by = self.user_id
            
            self.db.commit()
            
            return {
                "success": True,
                "journal_entry_id": journal_entry.id,
                "posting_rule_id": posting_rule.id,
                "message": "Transaction posted successfully"
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error posting transaction {ext_txn.id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def bulk_process_transactions(
        self, 
        connection_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Bulk process all unposted transactions from a connection
        """
        query = self.db.query(models.ExternalTransaction).filter(
            models.ExternalTransaction.company_id == self.company_id,
            models.ExternalTransaction.bank_connection_id == connection_id,
            models.ExternalTransaction.posting_status == "pending"
        )
        
        if from_date:
            query = query.filter(models.ExternalTransaction.transaction_date >= from_date)
        if to_date:
            query = query.filter(models.ExternalTransaction.transaction_date <= to_date)
        
        transactions = query.all()
        
        results = {
            "total": len(transactions),
            "posted": 0,
            "failed": 0,
            "manual_review": 0,
            "details": []
        }
        
        for txn in transactions:
            result = await self.process_external_transaction(txn.id)
            
            if result.get("success"):
                results["posted"] += 1
            elif result.get("requires_manual_review"):
                results["manual_review"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "transaction_id": txn.id,
                "result": result
            })
        
        return results
    
    def _find_matching_rule(
        self, 
        ext_txn: models.ExternalTransaction
    ) -> Optional[models.AutoPostingRule]:
        """
        Find the first matching posting rule based on priority
        """
        rules = self.db.query(models.AutoPostingRule).filter(
            models.AutoPostingRule.company_id == self.company_id,
            models.AutoPostingRule.is_active == True
        ).order_by(models.AutoPostingRule.priority.asc()).all()
        
        for rule in rules:
            if self._rule_matches_transaction(rule, ext_txn):
                return rule
        
        return None
    
    def _rule_matches_transaction(
        self, 
        rule: models.AutoPostingRule, 
        txn: models.ExternalTransaction
    ) -> bool:
        """
        Check if a posting rule matches the transaction
        """
        # Check transaction type
        if rule.transaction_type and rule.transaction_type != txn.transaction_type:
            return False
        
        # Check direction
        if rule.direction and rule.direction != txn.direction:
            return False
        
        # Check amount range
        if rule.min_amount is not None and txn.amount < rule.min_amount:
            return False
        if rule.max_amount is not None and txn.amount > rule.max_amount:
            return False
        
        # Check description contains
        if rule.description_contains:
            if not txn.description:
                return False
            keywords = rule.description_contains.lower().split(",")
            description_lower = txn.description.lower()
            if not any(keyword.strip() in description_lower for keyword in keywords):
                return False
        
        # Check counterparty contains
        if rule.counterparty_contains:
            if not txn.counterparty_name:
                return False
            keywords = rule.counterparty_contains.lower().split(",")
            counterparty_lower = txn.counterparty_name.lower()
            if not any(keyword.strip() in counterparty_lower for keyword in keywords):
                return False
        
        return True
    
    def _create_journal_entry(
        self, 
        ext_txn: models.ExternalTransaction,
        rule: models.AutoPostingRule
    ) -> models.JournalEntry:
        """
        Create journal entry based on posting rule
        """
        # Get bank GL account from connection
        bank_connection = self.db.query(models.BankConnection).filter(
            models.BankConnection.id == ext_txn.bank_connection_id
        ).first()
        
        if not bank_connection or not bank_connection.default_gl_account_id:
            raise ValueError("Bank connection must have default GL account")
        
        # Create journal entry header
        journal_entry = models.JournalEntry(
            company_id=self.company_id,
            entry_date=ext_txn.transaction_date,
            reference=f"AUTO-{ext_txn.external_transaction_id}",
            description=f"Auto-posted: {ext_txn.description or 'Bank Transaction'}",
            entry_type="auto_posted",
            source_type="bank_feed",
            source_id=ext_txn.id,
            created_by=self.user_id,
            status="posted"
        )
        self.db.add(journal_entry)
        self.db.flush()  # Get journal entry ID
        
        # Create line items based on direction and rule
        if ext_txn.direction == "inbound":
            # Money coming in
            # Debit: Bank Account
            self._create_line_item(
                journal_entry.id,
                bank_connection.default_gl_account_id,
                debit=ext_txn.amount,
                credit=0,
                description=f"Receipt from {ext_txn.counterparty_name or 'Unknown'}"
            )
            
            # Credit: Offset account from rule
            self._create_line_item(
                journal_entry.id,
                rule.offset_account_id,
                debit=0,
                credit=ext_txn.amount,
                description=f"Revenue/AR reduction: {ext_txn.description or ''}"
            )
            
            # Handle customer receipt if applicable
            if rule.auto_apply_to_ar and ext_txn.counterparty_name:
                self._apply_to_customer_invoice(ext_txn, journal_entry)
        
        else:
            # Money going out
            # Credit: Bank Account
            self._create_line_item(
                journal_entry.id,
                bank_connection.default_gl_account_id,
                debit=0,
                credit=ext_txn.amount,
                description=f"Payment to {ext_txn.counterparty_name or 'Unknown'}"
            )
            
            # Debit: Offset account from rule
            self._create_line_item(
                journal_entry.id,
                rule.offset_account_id,
                debit=ext_txn.amount,
                credit=0,
                description=f"Expense/AP reduction: {ext_txn.description or ''}"
            )
            
            # Handle supplier payment if applicable
            if rule.auto_apply_to_ap and ext_txn.counterparty_name:
                self._apply_to_supplier_bill(ext_txn, journal_entry)
        
        # Handle fees if any
        if ext_txn.fee and ext_txn.fee > 0 and rule.fee_account_id:
            self._post_transaction_fee(journal_entry.id, ext_txn, rule, bank_connection)
        
        return journal_entry
    
    def _create_line_item(
        self,
        journal_entry_id: int,
        account_id: int,
        debit: float,
        credit: float,
        description: str
    ):
        """Create a journal entry line item"""
        line = models.JournalEntryLine(
            journal_entry_id=journal_entry_id,
            account_id=account_id,
            debit_amount=debit,
            credit_amount=credit,
            description=description
        )
        self.db.add(line)
    
    def _post_transaction_fee(
        self,
        journal_entry_id: int,
        ext_txn: models.ExternalTransaction,
        rule: models.AutoPostingRule,
        bank_connection: models.BankConnection
    ):
        """Post bank/mobile money fees"""
        # Debit: Fee Expense Account
        self._create_line_item(
            journal_entry_id,
            rule.fee_account_id,
            debit=ext_txn.fee,
            credit=0,
            description="Transaction fees"
        )
        
        # Credit: Bank Account
        self._create_line_item(
            journal_entry_id,
            bank_connection.default_gl_account_id,
            debit=0,
            credit=ext_txn.fee,
            description="Transaction fees"
        )
    
    def _apply_to_customer_invoice(
        self,
        ext_txn: models.ExternalTransaction,
        journal_entry: models.JournalEntry
    ):
        """
        Auto-apply customer receipt to open invoices
        This is a placeholder - full implementation would match by customer and invoice
        """
        # TODO: Implement customer/invoice matching logic
        # - Find customer by counterparty_name
        # - Find open invoices for that customer
        # - Apply payment to oldest invoice first
        # - Create payment record linked to invoice
        logger.info(f"AR auto-application requested for {ext_txn.counterparty_name}")
    
    def _apply_to_supplier_bill(
        self,
        ext_txn: models.ExternalTransaction,
        journal_entry: models.JournalEntry
    ):
        """
        Auto-apply supplier payment to open bills
        This is a placeholder - full implementation would match by supplier and bill
        """
        # TODO: Implement supplier/bill matching logic
        # - Find supplier by counterparty_name
        # - Find open bills for that supplier
        # - Apply payment to oldest bill first
        # - Create payment record linked to bill
        logger.info(f"AP auto-application requested for {ext_txn.counterparty_name}")


class PostingRuleManager:
    """Manage auto-posting rules"""
    
    def __init__(self, db: Session, company_id: int):
        self.db = db
        self.company_id = company_id
    
    def create_default_rules(self):
        """Create default posting rules for common scenarios"""
        default_rules = [
            {
                "rule_name": "Customer Receipts - Sales Revenue",
                "description": "Auto-post customer payments to sales revenue",
                "transaction_type": "payment",
                "direction": "inbound",
                "min_amount": 0,
                "priority": 10,
                "auto_apply_to_ar": True,
                "is_active": True
            },
            {
                "rule_name": "Supplier Payments - Accounts Payable",
                "description": "Auto-post supplier payments to AP",
                "transaction_type": "payment",
                "direction": "outbound",
                "min_amount": 0,
                "priority": 20,
                "auto_apply_to_ap": True,
                "is_active": True
            },
            {
                "rule_name": "Bank Fees",
                "description": "Auto-post bank fees",
                "description_contains": "fee,charge,commission",
                "direction": "outbound",
                "priority": 5,
                "is_active": True
            }
        ]
        
        for rule_data in default_rules:
            rule = models.AutoPostingRule(
                company_id=self.company_id,
                **rule_data
            )
            self.db.add(rule)
        
        self.db.commit()
        return len(default_rules)

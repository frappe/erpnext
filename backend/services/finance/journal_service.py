"""
Finance - Journal Entry Service

Handles both compact and legacy journal entry formats per Finance PDF spec.

Compact Format:
{
  "total_amount": 1200.00,
  "currency": "ZMW",
  "entries": {
    "debits": [{"account_code": "1000-AR", "amount": 1200, "narration": "Invoice"}],
    "credits": [{"account_code": "4000-SALES", "amount": 1200, "narration": "Sale"}]
  }
}

Legacy Format:
{
  "lines": [
    {"account_code": "1000-AR", "side": "debit", "amount": 1200},
    {"account_code": "4000-SALES", "side": "credit", "amount": 1200}
  ]
}
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import date, datetime
from decimal import Decimal
import models
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class JournalLine:
    """Represents a single journal line (debit or credit)"""
    def __init__(self, account_code: str, account_id: str, side: str, amount: float, narration: str = ""):
        self.account_code = account_code
        self.account_id = account_id
        self.side = side  # "debit" or "credit"
        self.amount = amount
        self.narration = narration


class JournalEntryService:
    """
    Service for creating and managing journal entries
    Supports both compact and legacy formats
    """
    
    def __init__(self, db: Session, company_id: str, user_id: str):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
    
    def create_journal_entry(
        self,
        journal_number: str,
        entry_date: date,
        description: str,
        currency: str,
        data: Dict[str, Any],
        department_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        auto_post: bool = False
    ) -> models.JournalEntry:
        """
        Create journal entry from either compact or legacy format
        
        Args:
            journal_number: Unique journal number (e.g., JE-2025-001)
            entry_date: Entry date
            description: Entry description
            currency: Currency code (e.g., ZMW)
            data: Either compact format (with "entries") or legacy format (with "lines")
            department_id: Optional department
            branch_id: Optional branch
            source_type: Optional source (e.g., "invoice", "payment")
            source_id: Optional source ID
            auto_post: If True, automatically post the entry
        
        Returns:
            Created journal entry
        """
        
        # Parse journal lines from data
        journal_lines = self._parse_journal_data(data)
        
        # Validate balanced entry
        self._validate_balanced_entry(journal_lines)
        
        # Calculate total amount (sum of debits or credits)
        total_amount = sum(line.amount for line in journal_lines if line.side == "debit")
        
        # Create journal entry
        journal_entry = models.JournalEntry(
            company_id=self.company_id,
            department_id=department_id,
            branch_id=branch_id,
            journal_number=journal_number,
            date=entry_date,
            description=description,
            currency=currency,
            total_amount=total_amount,
            status="draft",
            created_by=self.user_id
        )
        
        self.db.add(journal_entry)
        self.db.flush()  # Get the ID
        
        # Create journal lines
        for line in journal_lines:
            journal_line = models.JournalLine(
                journal_id=journal_entry.id,
                account_id=line.account_id,
                side=line.side,
                amount=line.amount,
                narration=line.narration
            )
            self.db.add(journal_line)
        
        # Commit
        self.db.commit()
        self.db.refresh(journal_entry)
        
        # Auto-post if requested
        if auto_post:
            self.post_journal_entry(journal_entry.id)
        
        logger.info(f"Created journal entry {journal_number} with {len(journal_lines)} lines")
        
        return journal_entry
    
    def _parse_journal_data(self, data: Dict[str, Any]) -> List[JournalLine]:
        """
        Parse journal data from either compact or legacy format
        
        Compact format:
        {
          "entries": {
            "debits": [{"account_code": "1000", "amount": 100, "narration": "..."}],
            "credits": [{"account_code": "4000", "amount": 100, "narration": "..."}]
          }
        }
        
        Legacy format:
        {
          "lines": [
            {"account_code": "1000", "side": "debit", "amount": 100, "narration": "..."},
            {"account_code": "4000", "side": "credit", "amount": 100, "narration": "..."}
          ]
        }
        """
        
        journal_lines = []
        
        # Check for compact format
        if "entries" in data:
            # Compact format
            entries = data["entries"]
            
            # Process debits
            if "debits" in entries:
                for debit_entry in entries["debits"]:
                    account_id = self._get_account_id(debit_entry["account_code"])
                    journal_lines.append(
                        JournalLine(
                            account_code=debit_entry["account_code"],
                            account_id=account_id,
                            side="debit",
                            amount=float(debit_entry["amount"]),
                            narration=debit_entry.get("narration", "")
                        )
                    )
            
            # Process credits
            if "credits" in entries:
                for credit_entry in entries["credits"]:
                    account_id = self._get_account_id(credit_entry["account_code"])
                    journal_lines.append(
                        JournalLine(
                            account_code=credit_entry["account_code"],
                            account_id=account_id,
                            side="credit",
                            amount=float(credit_entry["amount"]),
                            narration=credit_entry.get("narration", "")
                        )
                    )
        
        # Check for legacy format
        elif "lines" in data:
            # Legacy format
            for line in data["lines"]:
                account_id = self._get_account_id(line["account_code"])
                journal_lines.append(
                    JournalLine(
                        account_code=line["account_code"],
                        account_id=account_id,
                        side=line["side"],
                        amount=float(line["amount"]),
                        narration=line.get("narration", "")
                    )
                )
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid journal entry format. Must include 'entries' (compact) or 'lines' (legacy)"
            )
        
        return journal_lines
    
    def _get_account_id(self, account_code: str) -> str:
        """Get account ID from account code"""
        account = self.db.query(models.Account).filter(
            models.Account.company_id == self.company_id,
            models.Account.code == account_code
        ).first()
        
        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"Account with code '{account_code}' not found"
            )
        
        return account.id
    
    def _validate_balanced_entry(self, journal_lines: List[JournalLine]):
        """Validate that debits equal credits"""
        total_debits = sum(line.amount for line in journal_lines if line.side == "debit")
        total_credits = sum(line.amount for line in journal_lines if line.side == "credit")
        
        # Allow small rounding differences (0.01)
        difference = abs(total_debits - total_credits)
        
        if difference > 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Journal entry is not balanced. Debits: {total_debits}, Credits: {total_credits}, Difference: {difference}"
            )
    
    def post_journal_entry(self, journal_id: str) -> models.JournalEntry:
        """
        Post a journal entry (change status from draft to posted)
        Posted entries cannot be edited
        """
        journal = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.id == journal_id,
            models.JournalEntry.company_id == self.company_id
        ).first()
        
        if not journal:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        
        if journal.status == "posted":
            raise HTTPException(status_code=400, detail="Journal entry is already posted")
        
        if journal.status == "locked":
            raise HTTPException(status_code=400, detail="Journal entry is locked and cannot be posted")
        
        # Validate balanced entry
        lines = self.db.query(models.JournalLine).filter(
            models.JournalLine.journal_id == journal_id
        ).all()
        
        total_debits = sum(line.amount for line in lines if line.side == "debit")
        total_credits = sum(line.amount for line in lines if line.side == "credit")
        
        if abs(total_debits - total_credits) > 0.01:
            raise HTTPException(
                status_code=400,
                detail="Cannot post unbalanced journal entry"
            )
        
        # Update status
        journal.status = "posted"
        self.db.commit()
        self.db.refresh(journal)
        
        logger.info(f"Posted journal entry {journal.journal_number}")
        
        return journal
    
    def reverse_journal_entry(
        self,
        journal_id: str,
        reversal_date: date,
        reversal_reason: str
    ) -> models.JournalEntry:
        """
        Reverse a journal entry by creating a reversing entry
        Per audit trail requirement: no editing, only corrective documents
        """
        # Get original entry
        original = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.id == journal_id,
            models.JournalEntry.company_id == self.company_id
        ).first()
        
        if not original:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        
        if original.status != "posted":
            raise HTTPException(status_code=400, detail="Can only reverse posted journal entries")
        
        # Get original lines
        original_lines = self.db.query(models.JournalLine).filter(
            models.JournalLine.journal_id == journal_id
        ).all()
        
        # Generate reversal journal number
        reversal_number = f"REV-{original.journal_number}"
        
        # Check if reversal already exists
        existing_reversal = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.journal_number == reversal_number
        ).first()
        
        if existing_reversal:
            raise HTTPException(status_code=400, detail="Reversal entry already exists")
        
        # Create reversal entry with swapped debits/credits
        reversal_lines = []
        for line in original_lines:
            account = self.db.query(models.Account).filter(
                models.Account.id == line.account_id
            ).first()
            
            # Swap debit and credit
            reversed_side = "credit" if line.side == "debit" else "debit"
            
            reversal_lines.append({
                "account_code": account.code,
                "side": reversed_side,
                "amount": line.amount,
                "narration": f"Reversal: {line.narration}"
            })
        
        # Create reversal using legacy format
        reversal_data = {"lines": reversal_lines}
        
        reversal_entry = self.create_journal_entry(
            journal_number=reversal_number,
            entry_date=reversal_date,
            description=f"REVERSAL: {original.description} - {reversal_reason}",
            currency=original.currency,
            data=reversal_data,
            department_id=original.department_id,
            branch_id=original.branch_id,
            source_type="reversal",
            source_id=original.id,
            auto_post=True
        )
        
        logger.info(f"Reversed journal entry {original.journal_number} with {reversal_number}")
        
        return reversal_entry
    
    def get_journal_entry(self, journal_id: str) -> Dict[str, Any]:
        """Get journal entry with all lines"""
        journal = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.id == journal_id,
            models.JournalEntry.company_id == self.company_id
        ).first()
        
        if not journal:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        
        # Get lines
        lines = self.db.query(models.JournalLine).filter(
            models.JournalLine.journal_id == journal_id
        ).all()
        
        # Get account details for each line
        line_details = []
        for line in lines:
            account = self.db.query(models.Account).filter(
                models.Account.id == line.account_id
            ).first()
            
            line_details.append({
                "id": line.id,
                "account_id": line.account_id,
                "account_code": account.code if account else None,
                "account_name": account.name if account else None,
                "side": line.side,
                "amount": line.amount,
                "narration": line.narration
            })
        
        return {
            "id": journal.id,
            "journal_number": journal.journal_number,
            "date": journal.date,
            "description": journal.description,
            "currency": journal.currency,
            "total_amount": journal.total_amount,
            "status": journal.status,
            "department_id": journal.department_id,
            "branch_id": journal.branch_id,
            "created_by": journal.created_by,
            "created_at": journal.created_at,
            "lines": line_details
        }
    
    def generate_journal_number(self) -> str:
        """Generate next journal number for the company"""
        # Get latest journal for this company
        latest = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.journal_number.like(f"JE-{datetime.now().year}-%")
        ).order_by(models.JournalEntry.journal_number.desc()).first()
        
        if latest:
            # Extract number from latest (e.g., JE-2025-0123 -> 123)
            try:
                parts = latest.journal_number.split("-")
                last_num = int(parts[-1])
                next_num = last_num + 1
            except:
                next_num = 1
        else:
            next_num = 1
        
        # Format: JE-YYYY-NNNN
        return f"JE-{datetime.now().year}-{next_num:04d}"

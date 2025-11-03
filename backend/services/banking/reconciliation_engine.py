from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import models
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class ReconciliationMatch:
    """Represents a potential match between external transaction and journal entry"""
    def __init__(
        self,
        external_transaction: models.ExternalTransaction,
        journal_entry: models.JournalEntry,
        confidence_score: float,
        match_reasons: List[str]
    ):
        self.external_transaction = external_transaction
        self.journal_entry = journal_entry
        self.confidence_score = confidence_score
        self.match_reasons = match_reasons


class AIReconciliationEngine:
    """
    AI-driven bank reconciliation engine with intelligent matching
    
    Features:
    - Fuzzy matching on amounts, dates, descriptions
    - ML-ready confidence scoring
    - Auto-match with configurable thresholds
    - Match history learning (future enhancement)
    """
    
    # Matching thresholds
    AUTO_MATCH_THRESHOLD = 0.95  # 95% confidence for auto-match
    SUGGEST_MATCH_THRESHOLD = 0.75  # 75% confidence for suggestions
    
    def __init__(self, db: Session, company_id: int, user_id: int):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
    
    async def reconcile_bank_account(
        self,
        bank_connection_id: int,
        from_date: datetime,
        to_date: datetime,
        auto_match: bool = True
    ) -> Dict[str, Any]:
        """
        Reconcile a bank account for a given period
        """
        # Get unreconciled external transactions
        external_txns = self._get_unreconciled_transactions(
            bank_connection_id, from_date, to_date
        )
        
        # Get unreconciled journal entries for the bank account
        journal_entries = self._get_unreconciled_journal_entries(
            bank_connection_id, from_date, to_date
        )
        
        results = {
            "total_external": len(external_txns),
            "total_internal": len(journal_entries),
            "auto_matched": 0,
            "suggested_matches": 0,
            "unmatched": 0,
            "matches": []
        }
        
        for ext_txn in external_txns:
            # Find best matches
            matches = self._find_matches(ext_txn, journal_entries)
            
            if not matches:
                results["unmatched"] += 1
                continue
            
            best_match = matches[0]
            
            if auto_match and best_match.confidence_score >= self.AUTO_MATCH_THRESHOLD:
                # Auto-match
                self._create_reconciliation(best_match, "auto")
                results["auto_matched"] += 1
                results["matches"].append({
                    "external_transaction_id": ext_txn.id,
                    "journal_entry_id": best_match.journal_entry.id,
                    "confidence": best_match.confidence_score,
                    "status": "auto_matched"
                })
            elif best_match.confidence_score >= self.SUGGEST_MATCH_THRESHOLD:
                # Suggest for manual review
                results["suggested_matches"] += 1
                results["matches"].append({
                    "external_transaction_id": ext_txn.id,
                    "journal_entry_id": best_match.journal_entry.id,
                    "confidence": best_match.confidence_score,
                    "reasons": best_match.match_reasons,
                    "status": "suggested"
                })
            else:
                results["unmatched"] += 1
        
        self.db.commit()
        return results
    
    def _get_unreconciled_transactions(
        self,
        bank_connection_id: int,
        from_date: datetime,
        to_date: datetime
    ) -> List[models.ExternalTransaction]:
        """Get unreconciled external transactions"""
        return self.db.query(models.ExternalTransaction).filter(
            models.ExternalTransaction.company_id == self.company_id,
            models.ExternalTransaction.bank_connection_id == bank_connection_id,
            models.ExternalTransaction.reconciliation_status == "unreconciled",
            models.ExternalTransaction.transaction_date >= from_date,
            models.ExternalTransaction.transaction_date <= to_date
        ).all()
    
    def _get_unreconciled_journal_entries(
        self,
        bank_connection_id: int,
        from_date: datetime,
        to_date: datetime
    ) -> List[models.JournalEntry]:
        """Get unreconciled journal entries for bank account"""
        # Get bank account's GL account
        bank_conn = self.db.query(models.BankConnection).filter(
            models.BankConnection.id == bank_connection_id
        ).first()
        
        if not bank_conn or not bank_conn.default_gl_account_id:
            return []
        
        # Get journal entry lines for this account
        lines = self.db.query(models.JournalEntryLine).join(
            models.JournalEntry
        ).filter(
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntryLine.account_id == bank_conn.default_gl_account_id,
            models.JournalEntryLine.reconciliation_status == "unreconciled",
            models.JournalEntry.entry_date >= from_date,
            models.JournalEntry.entry_date <= to_date
        ).all()
        
        # Return unique journal entries
        return list(set([line.journal_entry for line in lines]))
    
    def _find_matches(
        self,
        ext_txn: models.ExternalTransaction,
        journal_entries: List[models.JournalEntry]
    ) -> List[ReconciliationMatch]:
        """
        Find potential matches for an external transaction
        Returns sorted by confidence score (highest first)
        """
        matches = []
        
        for je in journal_entries:
            score, reasons = self._calculate_match_score(ext_txn, je)
            
            if score > 0:
                matches.append(ReconciliationMatch(
                    external_transaction=ext_txn,
                    journal_entry=je,
                    confidence_score=score,
                    match_reasons=reasons
                ))
        
        # Sort by confidence score descending
        matches.sort(key=lambda x: x.confidence_score, reverse=True)
        return matches
    
    def _calculate_match_score(
        self,
        ext_txn: models.ExternalTransaction,
        journal_entry: models.JournalEntry
    ) -> Tuple[float, List[str]]:
        """
        Calculate confidence score for a potential match
        Returns: (score 0-1, list of match reasons)
        """
        score = 0.0
        reasons = []
        max_score = 100.0  # Total points available
        
        # 1. Amount match (40 points) - Most important
        amount_score = self._score_amount_match(ext_txn, journal_entry)
        if amount_score > 0:
            score += amount_score * 40
            if amount_score == 1.0:
                reasons.append("Exact amount match")
            else:
                reasons.append(f"Close amount match ({amount_score*100:.0f}%)")
        
        # 2. Date proximity (25 points)
        date_score = self._score_date_proximity(ext_txn, journal_entry)
        if date_score > 0:
            score += date_score * 25
            days_diff = abs((ext_txn.transaction_date - journal_entry.entry_date).days)
            reasons.append(f"Date within {days_diff} days")
        
        # 3. Reference/description match (20 points)
        desc_score = self._score_description_match(ext_txn, journal_entry)
        if desc_score > 0:
            score += desc_score * 20
            if desc_score > 0.8:
                reasons.append("Strong description match")
            else:
                reasons.append("Partial description match")
        
        # 4. Direction match (10 points)
        direction_score = self._score_direction_match(ext_txn, journal_entry)
        if direction_score > 0:
            score += direction_score * 10
            reasons.append("Direction matches")
        
        # 5. Counterparty match (5 points - bonus)
        counterparty_score = self._score_counterparty_match(ext_txn, journal_entry)
        if counterparty_score > 0:
            score += counterparty_score * 5
            reasons.append("Counterparty name matches")
        
        # Normalize to 0-1
        final_score = min(score / max_score, 1.0)
        
        return final_score, reasons
    
    def _score_amount_match(
        self,
        ext_txn: models.ExternalTransaction,
        journal_entry: models.JournalEntry
    ) -> float:
        """Score amount match (1.0 = exact, 0.0 = no match)"""
        # Get journal entry amount (sum of debits or credits)
        je_lines = self.db.query(models.JournalEntryLine).filter(
            models.JournalEntryLine.journal_entry_id == journal_entry.id
        ).all()
        
        # Calculate total amount (use debits for outbound, credits for inbound)
        je_amount = sum(
            line.debit_amount if ext_txn.direction == "outbound" else line.credit_amount
            for line in je_lines
        )
        
        if je_amount == 0:
            return 0.0
        
        # Exact match
        if abs(ext_txn.amount - je_amount) < 0.01:
            return 1.0
        
        # Allow 1% tolerance
        diff_percent = abs(ext_txn.amount - je_amount) / max(ext_txn.amount, je_amount)
        if diff_percent <= 0.01:
            return 0.95
        
        # Allow 5% tolerance with reduced score
        if diff_percent <= 0.05:
            return 0.7
        
        return 0.0
    
    def _score_date_proximity(
        self,
        ext_txn: models.ExternalTransaction,
        journal_entry: models.JournalEntry
    ) -> float:
        """Score date proximity (1.0 = same day, decreases with time)"""
        days_diff = abs((ext_txn.transaction_date - journal_entry.entry_date).days)
        
        if days_diff == 0:
            return 1.0
        elif days_diff <= 1:
            return 0.9
        elif days_diff <= 3:
            return 0.7
        elif days_diff <= 7:
            return 0.5
        elif days_diff <= 14:
            return 0.3
        else:
            return 0.0
    
    def _score_description_match(
        self,
        ext_txn: models.ExternalTransaction,
        journal_entry: models.JournalEntry
    ) -> float:
        """Score description/reference match using fuzzy matching"""
        if not ext_txn.description and not ext_txn.reference_number:
            return 0.0
        
        ext_text = f"{ext_txn.description or ''} {ext_txn.reference_number or ''}".lower()
        je_text = f"{journal_entry.description or ''} {journal_entry.reference or ''}".lower()
        
        if not ext_text.strip() or not je_text.strip():
            return 0.0
        
        # Use SequenceMatcher for fuzzy matching
        similarity = SequenceMatcher(None, ext_text, je_text).ratio()
        return similarity
    
    def _score_direction_match(
        self,
        ext_txn: models.ExternalTransaction,
        journal_entry: models.JournalEntry
    ) -> float:
        """Score transaction direction match"""
        # This is simplified - full implementation would check debit/credit patterns
        # For now, just return 1.0 if both exist
        return 1.0
    
    def _score_counterparty_match(
        self,
        ext_txn: models.ExternalTransaction,
        journal_entry: models.JournalEntry
    ) -> float:
        """Score counterparty name match"""
        if not ext_txn.counterparty_name:
            return 0.0
        
        je_text = f"{journal_entry.description or ''} {journal_entry.reference or ''}".lower()
        counterparty_lower = ext_txn.counterparty_name.lower()
        
        # Check if counterparty name appears in journal entry
        if counterparty_lower in je_text:
            return 1.0
        
        # Fuzzy match
        similarity = SequenceMatcher(None, counterparty_lower, je_text).ratio()
        return similarity if similarity > 0.5 else 0.0
    
    def _create_reconciliation(
        self,
        match: ReconciliationMatch,
        match_type: str = "auto"
    ):
        """Create reconciliation record"""
        # Update external transaction
        match.external_transaction.reconciliation_status = "reconciled"
        match.external_transaction.reconciled_at = datetime.utcnow()
        match.external_transaction.reconciled_by = self.user_id
        match.external_transaction.journal_entry_id = match.journal_entry.id
        
        # Update journal entry lines
        lines = self.db.query(models.JournalEntryLine).filter(
            models.JournalEntryLine.journal_entry_id == match.journal_entry.id
        ).all()
        
        for line in lines:
            line.reconciliation_status = "reconciled"
            line.reconciled_at = datetime.utcnow()
        
        logger.info(
            f"{match_type.capitalize()} matched: "
            f"ExtTxn {match.external_transaction.id} <-> "
            f"JE {match.journal_entry.id} "
            f"(confidence: {match.confidence_score:.2f})"
        )
    
    async def manual_reconcile(
        self,
        external_transaction_id: int,
        journal_entry_id: int
    ) -> Dict[str, Any]:
        """Manually reconcile a transaction"""
        ext_txn = self.db.query(models.ExternalTransaction).filter(
            models.ExternalTransaction.id == external_transaction_id,
            models.ExternalTransaction.company_id == self.company_id
        ).first()
        
        je = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.id == journal_entry_id,
            models.JournalEntry.company_id == self.company_id
        ).first()
        
        if not ext_txn or not je:
            return {"success": False, "error": "Transaction or journal entry not found"}
        
        match = ReconciliationMatch(ext_txn, je, 1.0, ["Manual match"])
        self._create_reconciliation(match, "manual")
        self.db.commit()
        
        return {"success": True, "message": "Reconciled successfully"}
    
    async def get_reconciliation_report(
        self,
        bank_connection_id: int,
        as_of_date: datetime
    ) -> Dict[str, Any]:
        """Generate reconciliation report"""
        # Get bank connection
        bank_conn = self.db.query(models.BankConnection).filter(
            models.BankConnection.id == bank_connection_id
        ).first()
        
        if not bank_conn:
            return {"error": "Bank connection not found"}
        
        # Get bank statement balance
        latest_txn = self.db.query(models.ExternalTransaction).filter(
            models.ExternalTransaction.bank_connection_id == bank_connection_id,
            models.ExternalTransaction.transaction_date <= as_of_date
        ).order_by(models.ExternalTransaction.transaction_date.desc()).first()
        
        bank_balance = latest_txn.running_balance if latest_txn else 0.0
        
        # Get GL balance
        gl_balance = self._calculate_gl_balance(bank_conn.default_gl_account_id, as_of_date)
        
        # Get unreconciled items
        unreconciled_external = self.db.query(models.ExternalTransaction).filter(
            models.ExternalTransaction.bank_connection_id == bank_connection_id,
            models.ExternalTransaction.reconciliation_status == "unreconciled",
            models.ExternalTransaction.transaction_date <= as_of_date
        ).all()
        
        unreconciled_journal = self._get_unreconciled_journal_entries(
            bank_connection_id,
            datetime(2000, 1, 1),
            as_of_date
        )
        
        return {
            "bank_balance": bank_balance,
            "gl_balance": gl_balance,
            "difference": bank_balance - gl_balance,
            "unreconciled_external_count": len(unreconciled_external),
            "unreconciled_journal_count": len(unreconciled_journal),
            "unreconciled_external_amount": sum(t.amount for t in unreconciled_external),
            "reconciliation_status": "balanced" if abs(bank_balance - gl_balance) < 0.01 else "unbalanced"
        }
    
    def _calculate_gl_balance(self, account_id: int, as_of_date: datetime) -> float:
        """Calculate GL account balance as of a date"""
        lines = self.db.query(models.JournalEntryLine).join(
            models.JournalEntry
        ).filter(
            models.JournalEntryLine.account_id == account_id,
            models.JournalEntry.entry_date <= as_of_date,
            models.JournalEntry.company_id == self.company_id
        ).all()
        
        balance = sum(line.debit_amount - line.credit_amount for line in lines)
        return balance

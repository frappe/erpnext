"""
Finance - Foreign Exchange (FX) Revaluation Service

Implements multi-currency FX revaluation per Finance PDF spec:
- Store exchange rates (manual entry or API fetch)
- Calculate unrealized FX gains/losses
- Generate revaluation journal entries
- Support multiple currencies (USD, EUR, GBP, ZAR, etc.)
- Scheduled revaluation (month-end, quarter-end)

FX Revaluation Process:
1. Identify accounts marked for FX revaluation
2. Get current balances in foreign currency
3. Apply current exchange rate vs. original rate
4. Calculate unrealized gain/loss
5. Create revaluation journal entry
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


class FXRevaluationService:
    """
    Foreign Exchange Revaluation Service
    Handles multi-currency accounting and period-end revaluations
    """
    
    # Base currency (default for company)
    DEFAULT_BASE_CURRENCY = "ZMW"
    
    def __init__(self, db: Session, company_id: str, user_id: str):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
        
        # Get company's base currency
        company = self.db.query(models.Company).filter(
            models.Company.id == company_id
        ).first()
        self.base_currency = company.currency if company else self.DEFAULT_BASE_CURRENCY
    
    def add_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate: float,
        rate_date: date,
        rate_type: str = "official"  # official, market, custom
    ) -> models.ExchangeRate:
        """
        Add or update exchange rate for a date
        
        Args:
            from_currency: Source currency (e.g., USD)
            to_currency: Target currency (e.g., ZMW)
            rate: Exchange rate (e.g., 27.5 means 1 USD = 27.5 ZMW)
            rate_date: Date of the rate
            rate_type: Type of rate (official, market, custom)
        
        Returns:
            Created/updated exchange rate
        """
        # Check if rate exists for this date
        existing = self.db.query(models.ExchangeRate).filter(
            models.ExchangeRate.company_id == self.company_id,
            models.ExchangeRate.from_currency == from_currency,
            models.ExchangeRate.to_currency == to_currency,
            models.ExchangeRate.rate_date == rate_date
        ).first()
        
        if existing:
            # Update existing rate
            existing.rate = rate
            existing.rate_type = rate_type
            existing.updated_by = self.user_id
            existing.updated_at = datetime.now()
            
            self.db.commit()
            self.db.refresh(existing)
            
            logger.info(
                f"Updated exchange rate: {from_currency}/{to_currency} = {rate} on {rate_date}"
            )
            
            return existing
        else:
            # Create new rate
            exchange_rate = models.ExchangeRate(
                company_id=self.company_id,
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                rate_date=rate_date,
                rate_type=rate_type,
                created_by=self.user_id
            )
            
            self.db.add(exchange_rate)
            self.db.commit()
            self.db.refresh(exchange_rate)
            
            logger.info(
                f"Added exchange rate: {from_currency}/{to_currency} = {rate} on {rate_date}"
            )
            
            return exchange_rate
    
    def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: date
    ) -> Optional[float]:
        """
        Get exchange rate for a specific date
        If exact date not found, uses the most recent rate before that date
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            rate_date: Date to get rate for
        
        Returns:
            Exchange rate or None if not found
        """
        # Try exact date first
        rate = self.db.query(models.ExchangeRate).filter(
            models.ExchangeRate.company_id == self.company_id,
            models.ExchangeRate.from_currency == from_currency,
            models.ExchangeRate.to_currency == to_currency,
            models.ExchangeRate.rate_date == rate_date
        ).first()
        
        if rate:
            return float(rate.rate)
        
        # Fall back to most recent rate before this date
        rate = self.db.query(models.ExchangeRate).filter(
            models.ExchangeRate.company_id == self.company_id,
            models.ExchangeRate.from_currency == from_currency,
            models.ExchangeRate.to_currency == to_currency,
            models.ExchangeRate.rate_date <= rate_date
        ).order_by(models.ExchangeRate.rate_date.desc()).first()
        
        if rate:
            logger.info(
                f"Using rate from {rate.rate_date} for date {rate_date}: "
                f"{from_currency}/{to_currency} = {rate.rate}"
            )
            return float(rate.rate)
        
        logger.warning(
            f"No exchange rate found for {from_currency}/{to_currency} on or before {rate_date}"
        )
        return None
    
    def convert_amount(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        conversion_date: date
    ) -> Optional[Decimal]:
        """
        Convert amount from one currency to another
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            conversion_date: Date for rate lookup
        
        Returns:
            Converted amount or None if rate not available
        """
        if from_currency == to_currency:
            return amount
        
        rate = self.get_exchange_rate(from_currency, to_currency, conversion_date)
        
        if rate is None:
            return None
        
        return Decimal(str(amount)) * Decimal(str(rate))
    
    def perform_revaluation(
        self,
        revaluation_date: date,
        currencies: Optional[List[str]] = None,
        create_journal: bool = True
    ) -> Dict[str, Any]:
        """
        Perform FX revaluation for all foreign currency accounts
        
        Process:
        1. Find all accounts marked for FX revaluation
        2. Calculate unrealized gains/losses
        3. Optionally create revaluation journal entry
        
        Args:
            revaluation_date: Date to perform revaluation
            currencies: List of currencies to revalue (None = all)
            create_journal: If True, create journal entry
        
        Returns:
            Revaluation summary with gains/losses
        """
        # Get accounts marked for FX revaluation
        query = self.db.query(models.Account).filter(
            models.Account.company_id == self.company_id,
            models.Account.allow_fx_revaluation == True,
            models.Account.currency != None,
            models.Account.currency != self.base_currency
        )
        
        if currencies:
            query = query.filter(models.Account.currency.in_(currencies))
        
        fx_accounts = query.all()
        
        if not fx_accounts:
            return {
                "success": True,
                "message": "No accounts require FX revaluation",
                "revaluation_date": revaluation_date,
                "accounts_revalued": 0,
                "total_gain_loss": 0.0
            }
        
        revaluation_lines = []
        total_gain_loss = Decimal("0.00")
        
        for account in fx_accounts:
            # Calculate account balance in foreign currency
            fc_balance = self._get_account_balance_fc(account.id, revaluation_date)
            
            if fc_balance == 0:
                continue  # Skip zero balance accounts
            
            # Get current exchange rate
            current_rate = self.get_exchange_rate(
                from_currency=account.currency,
                to_currency=self.base_currency,
                rate_date=revaluation_date
            )
            
            if current_rate is None:
                logger.warning(
                    f"Skipping account {account.code}: No exchange rate for "
                    f"{account.currency}/{self.base_currency} on {revaluation_date}"
                )
                continue
            
            # Calculate current value in base currency
            current_value_base = Decimal(str(fc_balance)) * Decimal(str(current_rate))
            
            # Get book value in base currency (from journal lines)
            book_value_base = self._get_account_balance(account.id, revaluation_date)
            
            # Calculate unrealized gain/loss
            unrealized_gain_loss = current_value_base - Decimal(str(book_value_base))
            
            if abs(unrealized_gain_loss) < Decimal("0.01"):
                continue  # Skip insignificant differences
            
            total_gain_loss += unrealized_gain_loss
            
            revaluation_lines.append({
                "account_id": account.id,
                "account_code": account.code,
                "account_name": account.name,
                "currency": account.currency,
                "fc_balance": float(fc_balance),
                "exchange_rate": current_rate,
                "current_value_base": float(current_value_base),
                "book_value_base": float(book_value_base),
                "unrealized_gain_loss": float(unrealized_gain_loss)
            })
        
        # Create revaluation journal entry if requested
        journal_entry_id = None
        
        if create_journal and revaluation_lines:
            journal_entry_id = self._create_revaluation_journal(
                revaluation_date=revaluation_date,
                revaluation_lines=revaluation_lines,
                total_gain_loss=total_gain_loss
            )
        
        return {
            "success": True,
            "revaluation_date": revaluation_date,
            "accounts_revalued": len(revaluation_lines),
            "total_gain_loss": float(total_gain_loss),
            "revaluation_lines": revaluation_lines,
            "journal_entry_id": journal_entry_id
        }
    
    def _get_account_balance_fc(self, account_id: str, as_of_date: date) -> Decimal:
        """Get account balance in foreign currency (sum of debits - credits)"""
        debits = self.db.query(func.sum(models.JournalLine.amount)).join(
            models.JournalEntry
        ).filter(
            models.JournalLine.account_id == account_id,
            models.JournalLine.side == "debit",
            models.JournalEntry.date <= as_of_date,
            models.JournalEntry.status.in_(["posted", "locked"])
        ).scalar() or 0
        
        credits = self.db.query(func.sum(models.JournalLine.amount)).join(
            models.JournalEntry
        ).filter(
            models.JournalLine.account_id == account_id,
            models.JournalLine.side == "credit",
            models.JournalEntry.date <= as_of_date,
            models.JournalEntry.status.in_(["posted", "locked"])
        ).scalar() or 0
        
        return Decimal(str(debits)) - Decimal(str(credits))
    
    def _get_account_balance(self, account_id: str, as_of_date: date) -> Decimal:
        """Get account balance in base currency"""
        return self._get_account_balance_fc(account_id, as_of_date)
    
    def _create_revaluation_journal(
        self,
        revaluation_date: date,
        revaluation_lines: List[Dict[str, Any]],
        total_gain_loss: Decimal
    ) -> str:
        """
        Create journal entry for FX revaluation
        
        Journal Entry Structure:
        - Debit/Credit: Foreign currency accounts (unrealized gain/loss)
        - Credit/Debit: FX Gain/Loss account
        """
        from .journal_service import JournalEntryService
        
        # Get or create FX Gain/Loss account
        fx_gl_account = self._get_fx_gain_loss_account()
        
        # Build journal lines
        journal_lines = []
        
        for line in revaluation_lines:
            gain_loss = Decimal(str(line["unrealized_gain_loss"]))
            
            if gain_loss > 0:
                # Unrealized gain: Debit asset/expense, Credit FX gain
                journal_lines.append({
                    "account_code": line["account_code"],
                    "side": "debit",
                    "amount": abs(float(gain_loss)),
                    "narration": f"FX revaluation gain: {line['currency']}"
                })
            else:
                # Unrealized loss: Credit asset/expense, Debit FX loss
                journal_lines.append({
                    "account_code": line["account_code"],
                    "side": "credit",
                    "amount": abs(float(gain_loss)),
                    "narration": f"FX revaluation loss: {line['currency']}"
                })
        
        # Add FX Gain/Loss contra entry
        if total_gain_loss > 0:
            # Total gain: Credit FX Gain account
            journal_lines.append({
                "account_code": fx_gl_account.code,
                "side": "credit",
                "amount": abs(float(total_gain_loss)),
                "narration": "FX revaluation gain"
            })
        else:
            # Total loss: Debit FX Loss account
            journal_lines.append({
                "account_code": fx_gl_account.code,
                "side": "debit",
                "amount": abs(float(total_gain_loss)),
                "narration": "FX revaluation loss"
            })
        
        # Create journal entry
        journal_service = JournalEntryService(self.db, self.company_id, self.user_id)
        
        journal_data = {"lines": journal_lines}
        
        journal_entry = journal_service.create_journal_entry(
            journal_number=journal_service.generate_journal_number(),
            entry_date=revaluation_date,
            description=f"FX Revaluation - {revaluation_date}",
            currency=self.base_currency,
            data=journal_data,
            source_type="fx_revaluation",
            auto_post=True
        )
        
        logger.info(
            f"Created FX revaluation journal {journal_entry.journal_number}: "
            f"{len(revaluation_lines)} accounts, "
            f"{'gain' if total_gain_loss > 0 else 'loss'} of {abs(total_gain_loss)}"
        )
        
        return journal_entry.id
    
    def _get_fx_gain_loss_account(self) -> models.Account:
        """Get or create FX Gain/Loss account"""
        account = self.db.query(models.Account).filter(
            models.Account.company_id == self.company_id,
            models.Account.code == "7900-FXGL"
        ).first()
        
        if not account:
            # Create FX Gain/Loss account
            account = models.Account(
                company_id=self.company_id,
                code="7900-FXGL",
                name="Foreign Exchange Gain/Loss",
                account_type="revenue",  # Or "expense" depending on setup
                description="Unrealized FX gains and losses from revaluation",
                is_active=True
            )
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
            
            logger.info("Created FX Gain/Loss account: 7900-FXGL")
        
        return account
    
    def get_revaluation_history(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get history of FX revaluations
        
        Returns journal entries with source_type = 'fx_revaluation'
        """
        query = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.source_type == "fx_revaluation"
        )
        
        if from_date:
            query = query.filter(models.JournalEntry.date >= from_date)
        if to_date:
            query = query.filter(models.JournalEntry.date <= to_date)
        
        journals = query.order_by(models.JournalEntry.date.desc()).all()
        
        return [
            {
                "id": j.id,
                "journal_number": j.journal_number,
                "date": j.date,
                "description": j.description,
                "total_amount": j.total_amount,
                "status": j.status,
                "created_at": j.created_at
            }
            for j in journals
        ]

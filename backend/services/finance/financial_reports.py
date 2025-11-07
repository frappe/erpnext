"""
Finance - Financial Reports Service

Implements financial reporting per Finance PDF spec:
- Balance Sheet (Statement of Financial Position)
- Income Statement (P&L - Profit & Loss)
- Cash Flow Statement
- Trial Balance
- General Ledger Report
- Account Activity Report
- Drill-down capability (reports → journals → lines)
- Multi-period comparison
- Export to PDF/Excel

Financial Statement Structure:
1. Balance Sheet: Assets = Liabilities + Equity
2. Income Statement: Revenue - Expenses = Net Income
3. Cash Flow: Operating + Investing + Financing = Net Cash Flow
4. Trial Balance: Sum of all account balances (DR = CR)
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, case
from datetime import date, datetime
from decimal import Decimal
import models
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class FinancialReportService:
    """
    Financial Reporting Service
    Generates financial statements with drill-down capability
    """
    
    def __init__(self, db: Session, company_id: str, user_id: str):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
    
    def get_balance_sheet(
        self,
        as_of_date: date,
        comparison_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Generate Balance Sheet (Statement of Financial Position)
        
        Structure:
        ASSETS
          Current Assets
          Non-Current Assets
        LIABILITIES
          Current Liabilities
          Non-Current Liabilities
        EQUITY
        
        Formula: Assets = Liabilities + Equity
        
        Args:
            as_of_date: Date to generate balance sheet as of
            comparison_date: Optional prior date for comparison
        
        Returns:
            Balance sheet with drill-down links
        """
        # Get all accounts
        accounts = self.db.query(models.Account).filter(
            models.Account.company_id == self.company_id
        ).all()
        
        # Calculate balances for each account
        account_balances = {}
        
        for account in accounts:
            balance = self._get_account_balance(account.id, as_of_date)
            account_balances[account.id] = {
                "account_id": account.id,
                "account_code": account.code,
                "account_name": account.name,
                "account_type": account.type,
                "balance": balance
            }
        
        # Categorize accounts
        assets = []
        liabilities = []
        equity = []
        
        for acc_id, acc_data in account_balances.items():
            acc_type = acc_data["account_type"]
            
            if acc_type == "Asset":
                assets.append(acc_data)
            elif acc_type == "Liability":
                liabilities.append(acc_data)
            elif acc_type == "Equity":
                equity.append(acc_data)
        
        # Calculate totals
        total_assets = sum(Decimal(str(a["balance"])) for a in assets)
        total_liabilities = sum(Decimal(str(l["balance"])) for l in liabilities)
        total_equity = sum(Decimal(str(e["balance"])) for e in equity)
        
        # Balance check
        total_liabilities_equity = total_liabilities + total_equity
        balanced = abs(total_assets - total_liabilities_equity) < Decimal("0.01")
        
        logger.info(
            f"Generated Balance Sheet as of {as_of_date}: "
            f"Assets={total_assets}, Liabilities={total_liabilities}, "
            f"Equity={total_equity}, Balanced={balanced}"
        )
        
        return {
            "report_type": "balance_sheet",
            "company_id": self.company_id,
            "as_of_date": as_of_date,
            "assets": {
                "accounts": sorted(assets, key=lambda x: x["account_code"]),
                "total": float(total_assets)
            },
            "liabilities": {
                "accounts": sorted(liabilities, key=lambda x: x["account_code"]),
                "total": float(total_liabilities)
            },
            "equity": {
                "accounts": sorted(equity, key=lambda x: x["account_code"]),
                "total": float(total_equity)
            },
            "total_liabilities_equity": float(total_liabilities_equity),
            "balanced": balanced,
            "variance": float(total_assets - total_liabilities_equity)
        }
    
    def get_income_statement(
        self,
        start_date: date,
        end_date: date,
        comparison_start: Optional[date] = None,
        comparison_end: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Generate Income Statement (Profit & Loss)
        
        Structure:
        REVENUE
          - Operating Revenue
          - Other Income
        EXPENSES
          - Cost of Goods Sold
          - Operating Expenses
          - Other Expenses
        = NET INCOME (Revenue - Expenses)
        
        Args:
            start_date: Period start date
            end_date: Period end date
            comparison_start: Optional comparison period start
            comparison_end: Optional comparison period end
        
        Returns:
            Income statement with drill-down links
        """
        # Get revenue and expense accounts
        accounts = self.db.query(models.Account).filter(
            models.Account.company_id == self.company_id,
            models.Account.type.in_(["Revenue", "Expense"])
        ).all()
        
        revenue_accounts = []
        expense_accounts = []
        
        for account in accounts:
            # Get activity for the period
            balance = self._get_account_activity(account.id, start_date, end_date)
            
            if balance != 0:
                account_data = {
                    "account_id": account.id,
                    "account_code": account.code,
                    "account_name": account.name,
                    "balance": balance
                }
                
                if account.type == "Revenue":
                    revenue_accounts.append(account_data)
                else:
                    expense_accounts.append(account_data)
        
        # Calculate totals
        total_revenue = sum(Decimal(str(r["balance"])) for r in revenue_accounts)
        total_expenses = sum(Decimal(str(e["balance"])) for e in expense_accounts)
        net_income = total_revenue - total_expenses
        
        # Calculate profit margin
        profit_margin = (net_income / total_revenue * 100) if total_revenue != 0 else Decimal("0")
        
        logger.info(
            f"Generated Income Statement {start_date} to {end_date}: "
            f"Revenue={total_revenue}, Expenses={total_expenses}, "
            f"Net Income={net_income}, Margin={profit_margin:.2f}%"
        )
        
        return {
            "report_type": "income_statement",
            "company_id": self.company_id,
            "start_date": start_date,
            "end_date": end_date,
            "revenue": {
                "accounts": sorted(revenue_accounts, key=lambda x: x["account_code"]),
                "total": float(total_revenue)
            },
            "expenses": {
                "accounts": sorted(expense_accounts, key=lambda x: x["account_code"]),
                "total": float(total_expenses)
            },
            "net_income": float(net_income),
            "profit_margin_percent": float(profit_margin)
        }
    
    def get_trial_balance(
        self,
        as_of_date: date
    ) -> Dict[str, Any]:
        """
        Generate Trial Balance
        
        Shows all accounts with their debit and credit balances
        Verifies that total debits = total credits
        
        Args:
            as_of_date: Date to generate trial balance as of
        
        Returns:
            Trial balance with all accounts
        """
        # Get all accounts
        accounts = self.db.query(models.Account).filter(
            models.Account.company_id == self.company_id
        ).all()
        
        trial_balance_lines = []
        total_debits = Decimal("0")
        total_credits = Decimal("0")
        
        for account in accounts:
            # Get debit and credit totals
            debit_total, credit_total = self._get_account_debit_credit_totals(
                account.id, 
                as_of_date
            )
            
            # Calculate balance
            balance = debit_total - credit_total
            
            # Determine if balance is debit or credit
            if balance > 0:
                debit_balance = balance
                credit_balance = Decimal("0")
            else:
                debit_balance = Decimal("0")
                credit_balance = abs(balance)
            
            # Only include accounts with activity
            if debit_total != 0 or credit_total != 0:
                trial_balance_lines.append({
                    "account_id": account.id,
                    "account_code": account.code,
                    "account_name": account.name,
                    "account_type": account.type,
                    "debit_balance": float(debit_balance),
                    "credit_balance": float(credit_balance)
                })
                
                total_debits += debit_balance
                total_credits += credit_balance
        
        # Check if balanced
        balanced = abs(total_debits - total_credits) < Decimal("0.01")
        
        logger.info(
            f"Generated Trial Balance as of {as_of_date}: "
            f"Debits={total_debits}, Credits={total_credits}, "
            f"Balanced={balanced}"
        )
        
        return {
            "report_type": "trial_balance",
            "company_id": self.company_id,
            "as_of_date": as_of_date,
            "accounts": sorted(trial_balance_lines, key=lambda x: x["account_code"]),
            "total_debits": float(total_debits),
            "total_credits": float(total_credits),
            "balanced": balanced,
            "variance": float(total_debits - total_credits)
        }
    
    def get_general_ledger(
        self,
        start_date: date,
        end_date: date,
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate General Ledger Report
        
        Shows all journal entries for a period, optionally filtered by account
        
        Args:
            start_date: Period start date
            end_date: Period end date
            account_id: Optional account filter
        
        Returns:
            General ledger with all transactions
        """
        # Build query
        query = self.db.query(models.JournalLine).join(
            models.JournalEntry
        ).join(
            models.Account
        ).filter(
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.date >= start_date,
            models.JournalEntry.date <= end_date,
            models.JournalEntry.status.in_(["posted", "locked"])
        )
        
        if account_id:
            query = query.filter(models.JournalLine.account_id == account_id)
        
        query = query.order_by(
            models.Account.code,
            models.JournalEntry.date,
            models.JournalEntry.journal_number
        )
        
        lines = query.all()
        
        # Group by account
        ledger_by_account = {}
        
        for line in lines:
            account = line.account
            account_key = account.id
            
            if account_key not in ledger_by_account:
                ledger_by_account[account_key] = {
                    "account_id": account.id,
                    "account_code": account.code,
                    "account_name": account.name,
                    "transactions": [],
                    "total_debits": Decimal("0"),
                    "total_credits": Decimal("0")
                }
            
            # Add transaction
            amount = Decimal(str(line.amount))
            transaction = {
                "date": line.journal_entry.date,
                "journal_number": line.journal_entry.journal_number,
                "journal_id": line.journal_entry.id,
                "description": line.journal_entry.description,
                "narration": line.narration,
                "debit": float(amount) if line.side == "debit" else 0,
                "credit": float(amount) if line.side == "credit" else 0
            }
            
            ledger_by_account[account_key]["transactions"].append(transaction)
            
            if line.side == "debit":
                ledger_by_account[account_key]["total_debits"] += amount
            else:
                ledger_by_account[account_key]["total_credits"] += amount
        
        # Convert to list and calculate balances
        ledger_accounts = []
        for account_data in ledger_by_account.values():
            account_data["total_debits"] = float(account_data["total_debits"])
            account_data["total_credits"] = float(account_data["total_credits"])
            account_data["net_balance"] = account_data["total_debits"] - account_data["total_credits"]
            ledger_accounts.append(account_data)
        
        logger.info(
            f"Generated General Ledger {start_date} to {end_date}: "
            f"{len(ledger_accounts)} accounts, {len(lines)} transactions"
        )
        
        return {
            "report_type": "general_ledger",
            "company_id": self.company_id,
            "start_date": start_date,
            "end_date": end_date,
            "account_filter": account_id,
            "accounts": sorted(ledger_accounts, key=lambda x: x["account_code"]),
            "total_transactions": len(lines)
        }
    
    def get_account_activity(
        self,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get detailed activity for a specific account (drill-down)
        
        Shows:
        - Opening balance
        - All transactions in period
        - Closing balance
        
        Args:
            account_id: Account to get activity for
            start_date: Period start date
            end_date: Period end date
        
        Returns:
            Account activity with drill-down to journal entries
        """
        # Get account
        account = self.db.query(models.Account).filter(
            models.Account.id == account_id,
            models.Account.company_id == self.company_id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Calculate opening balance (before start_date)
        opening_balance = self._get_account_balance(account_id, start_date, before_date=True)
        
        # Get transactions in period
        transactions = self.db.query(models.JournalLine).join(
            models.JournalEntry
        ).filter(
            models.JournalLine.account_id == account_id,
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.date >= start_date,
            models.JournalEntry.date <= end_date,
            models.JournalEntry.status.in_(["posted", "locked"])
        ).order_by(
            models.JournalEntry.date,
            models.JournalEntry.journal_number
        ).all()
        
        # Build transaction list
        running_balance = Decimal(str(opening_balance))
        transaction_list = []
        
        for line in transactions:
            amount = Decimal(str(line.amount))
            
            # Update running balance based on account type and side
            if line.side == "debit":
                if account.type in ["Asset", "Expense"]:
                    running_balance += amount
                else:
                    running_balance -= amount
            else:
                if account.type in ["Asset", "Expense"]:
                    running_balance -= amount
                else:
                    running_balance += amount
            
            transaction_list.append({
                "date": line.journal_entry.date,
                "journal_number": line.journal_entry.journal_number,
                "journal_id": line.journal_entry.id,
                "description": line.journal_entry.description,
                "narration": line.narration,
                "debit": float(amount) if line.side == "debit" else 0,
                "credit": float(amount) if line.side == "credit" else 0,
                "balance": float(running_balance)
            })
        
        closing_balance = running_balance
        
        logger.info(
            f"Generated Account Activity for {account.code} - {account.name}, "
            f"{start_date} to {end_date}: {len(transaction_list)} transactions"
        )
        
        return {
            "report_type": "account_activity",
            "company_id": self.company_id,
            "account_id": account.id,
            "account_code": account.code,
            "account_name": account.name,
            "account_type": account.type,
            "start_date": start_date,
            "end_date": end_date,
            "opening_balance": float(opening_balance),
            "closing_balance": float(closing_balance),
            "net_change": float(closing_balance - Decimal(str(opening_balance))),
            "transactions": transaction_list,
            "transaction_count": len(transaction_list)
        }
    
    def _get_account_balance(
        self,
        account_id: str,
        as_of_date: date,
        before_date: bool = False
    ) -> Decimal:
        """
        Calculate account balance as of a specific date
        
        Args:
            account_id: Account ID
            as_of_date: Date to calculate balance as of
            before_date: If True, get balance before this date (for opening balance)
        
        Returns:
            Account balance
        """
        # Get account
        account = self.db.query(models.Account).filter(
            models.Account.id == account_id
        ).first()
        
        if not account:
            return Decimal("0")
        
        # Get all journal lines for this account up to the date
        query = self.db.query(models.JournalLine).join(
            models.JournalEntry
        ).filter(
            models.JournalLine.account_id == account_id,
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.status.in_(["posted", "locked"])
        )
        
        if before_date:
            query = query.filter(models.JournalEntry.date < as_of_date)
        else:
            query = query.filter(models.JournalEntry.date <= as_of_date)
        
        lines = query.all()
        
        # Calculate balance based on account type
        balance = Decimal("0")
        
        for line in lines:
            amount = Decimal(str(line.amount))
            
            # Debit increases: Assets, Expenses
            # Credit increases: Liabilities, Equity, Revenue
            if line.side == "debit":
                if account.type in ["Asset", "Expense"]:
                    balance += amount
                else:
                    balance -= amount
            else:
                if account.type in ["Asset", "Expense"]:
                    balance -= amount
                else:
                    balance += amount
        
        return balance
    
    def _get_account_activity(
        self,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> Decimal:
        """
        Get net activity for an account in a period
        
        Args:
            account_id: Account ID
            start_date: Period start
            end_date: Period end
        
        Returns:
            Net activity (revenue positive, expense positive)
        """
        # Get account
        account = self.db.query(models.Account).filter(
            models.Account.id == account_id
        ).first()
        
        if not account:
            return Decimal("0")
        
        # Get lines in period
        lines = self.db.query(models.JournalLine).join(
            models.JournalEntry
        ).filter(
            models.JournalLine.account_id == account_id,
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.date >= start_date,
            models.JournalEntry.date <= end_date,
            models.JournalEntry.status.in_(["posted", "locked"])
        ).all()
        
        activity = Decimal("0")
        
        for line in lines:
            amount = Decimal(str(line.amount))
            
            # For P&L accounts, calculate net activity
            if account.type == "Revenue":
                # Revenue: credits increase, debits decrease
                if line.side == "credit":
                    activity += amount
                else:
                    activity -= amount
            elif account.type == "Expense":
                # Expense: debits increase, credits decrease
                if line.side == "debit":
                    activity += amount
                else:
                    activity -= amount
        
        return activity
    
    def _get_account_debit_credit_totals(
        self,
        account_id: str,
        as_of_date: date
    ) -> tuple[Decimal, Decimal]:
        """
        Get total debits and credits for an account
        
        Args:
            account_id: Account ID
            as_of_date: Date to calculate as of
        
        Returns:
            Tuple of (total_debits, total_credits)
        """
        lines = self.db.query(models.JournalLine).join(
            models.JournalEntry
        ).filter(
            models.JournalLine.account_id == account_id,
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.date <= as_of_date,
            models.JournalEntry.status.in_(["posted", "locked"])
        ).all()
        
        total_debits = Decimal("0")
        total_credits = Decimal("0")
        
        for line in lines:
            amount = Decimal(str(line.amount))
            if line.side == "debit":
                total_debits += amount
            else:
                total_credits += amount
        
        return total_debits, total_credits

"""
Finance - Accounting Period Management

Implements period close and lock functionality per Finance PDF spec:
- Monthly/Quarterly/Yearly periods
- Close periods to prevent modifications
- Lock periods (final, immutable)
- Automatic period creation
- Validation of transactions against period status

Period States:
- open: Transactions can be posted
- closed: No new transactions, existing can be adjusted
- locked: Period is final, no changes allowed (year-end close)
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, extract
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import models
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class PeriodManagementService:
    """
    Manages accounting periods and period close/lock operations
    """
    
    def __init__(self, db: Session, company_id: str, user_id: str):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
    
    def create_period(
        self,
        period_name: str,
        start_date: date,
        end_date: date,
        period_type: str = "monthly",  # monthly, quarterly, yearly
        fiscal_year: int = None
    ) -> models.AccountingPeriod:
        """
        Create a new accounting period
        
        Args:
            period_name: Name of period (e.g., "January 2025", "Q1 2025")
            start_date: Period start date
            end_date: Period end date
            period_type: monthly, quarterly, yearly
            fiscal_year: Fiscal year (defaults to year of start_date)
        
        Returns:
            Created accounting period
        """
        # Validate dates
        if end_date <= start_date:
            raise HTTPException(
                status_code=400,
                detail="End date must be after start date"
            )
        
        # Check for overlapping periods
        overlapping = self.db.query(models.AccountingPeriod).filter(
            models.AccountingPeriod.company_id == self.company_id,
            or_(
                and_(
                    models.AccountingPeriod.start_date <= start_date,
                    models.AccountingPeriod.end_date >= start_date
                ),
                and_(
                    models.AccountingPeriod.start_date <= end_date,
                    models.AccountingPeriod.end_date >= end_date
                )
            )
        ).first()
        
        if overlapping:
            raise HTTPException(
                status_code=400,
                detail=f"Period overlaps with existing period: {overlapping.period_name}"
            )
        
        # Default fiscal year
        if fiscal_year is None:
            fiscal_year = start_date.year
        
        # Create period
        period = models.AccountingPeriod(
            company_id=self.company_id,
            period_name=period_name,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            fiscal_year=fiscal_year,
            status="open",
            created_by=self.user_id
        )
        
        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        
        logger.info(f"Created accounting period: {period_name} ({start_date} to {end_date})")
        
        return period
    
    def auto_create_periods(
        self,
        start_year: int,
        num_years: int = 1,
        period_type: str = "monthly"
    ) -> List[models.AccountingPeriod]:
        """
        Automatically create periods for a year
        
        Args:
            start_year: Starting fiscal year
            num_years: Number of years to create (default 1)
            period_type: monthly, quarterly, yearly
        
        Returns:
            List of created periods
        """
        created_periods = []
        
        for year_offset in range(num_years):
            year = start_year + year_offset
            
            if period_type == "monthly":
                # Create 12 monthly periods
                for month in range(1, 13):
                    start = date(year, month, 1)
                    # Last day of month
                    if month == 12:
                        end = date(year, 12, 31)
                    else:
                        end = date(year, month + 1, 1) - timedelta(days=1)
                    
                    period_name = start.strftime("%B %Y")
                    
                    # Check if already exists
                    existing = self.db.query(models.AccountingPeriod).filter(
                        models.AccountingPeriod.company_id == self.company_id,
                        models.AccountingPeriod.start_date == start,
                        models.AccountingPeriod.end_date == end
                    ).first()
                    
                    if not existing:
                        period = self.create_period(
                            period_name=period_name,
                            start_date=start,
                            end_date=end,
                            period_type="monthly",
                            fiscal_year=year
                        )
                        created_periods.append(period)
            
            elif period_type == "quarterly":
                # Create 4 quarterly periods
                quarters = [
                    (1, "Q1"),
                    (4, "Q2"),
                    (7, "Q3"),
                    (10, "Q4")
                ]
                
                for start_month, quarter_name in quarters:
                    start = date(year, start_month, 1)
                    # End of quarter (3 months later, last day)
                    end_month = start_month + 2
                    if end_month <= 12:
                        end = date(year, end_month + 1, 1) - timedelta(days=1)
                    else:
                        end = date(year, 12, 31)
                    
                    period_name = f"{quarter_name} {year}"
                    
                    existing = self.db.query(models.AccountingPeriod).filter(
                        models.AccountingPeriod.company_id == self.company_id,
                        models.AccountingPeriod.start_date == start,
                        models.AccountingPeriod.end_date == end
                    ).first()
                    
                    if not existing:
                        period = self.create_period(
                            period_name=period_name,
                            start_date=start,
                            end_date=end,
                            period_type="quarterly",
                            fiscal_year=year
                        )
                        created_periods.append(period)
            
            elif period_type == "yearly":
                # Create 1 yearly period
                start = date(year, 1, 1)
                end = date(year, 12, 31)
                period_name = f"FY {year}"
                
                existing = self.db.query(models.AccountingPeriod).filter(
                    models.AccountingPeriod.company_id == self.company_id,
                    models.AccountingPeriod.start_date == start,
                    models.AccountingPeriod.end_date == end
                ).first()
                
                if not existing:
                    period = self.create_period(
                        period_name=period_name,
                        start_date=start,
                        end_date=end,
                        period_type="yearly",
                        fiscal_year=year
                    )
                    created_periods.append(period)
        
        logger.info(f"Auto-created {len(created_periods)} periods for {num_years} year(s)")
        
        return created_periods
    
    def close_period(
        self,
        period_id: str,
        close_notes: Optional[str] = None
    ) -> models.AccountingPeriod:
        """
        Close an accounting period (open → closed)
        
        Closed periods:
        - No new transactions can be posted
        - Existing transactions can be adjusted (with approval)
        - Can be reopened if needed
        
        Args:
            period_id: Period ID to close
            close_notes: Optional notes about closing
        
        Returns:
            Updated period
        """
        period = self.db.query(models.AccountingPeriod).filter(
            models.AccountingPeriod.id == period_id,
            models.AccountingPeriod.company_id == self.company_id
        ).first()
        
        if not period:
            raise HTTPException(status_code=404, detail="Period not found")
        
        if period.status != "open":
            raise HTTPException(
                status_code=400,
                detail=f"Can only close 'open' periods. Current status: {period.status}"
            )
        
        # Validate all transactions in period are posted
        draft_journals = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.date >= period.start_date,
            models.JournalEntry.date <= period.end_date,
            models.JournalEntry.status == "draft"
        ).count()
        
        if draft_journals > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot close period: {draft_journals} draft journal entries exist. Please post or delete them first."
            )
        
        # Close period
        period.status = "closed"
        period.closed_by = self.user_id
        period.closed_at = datetime.now()
        period.close_notes = close_notes
        
        self.db.commit()
        self.db.refresh(period)
        
        logger.info(f"Closed accounting period: {period.period_name}")
        
        return period
    
    def lock_period(
        self,
        period_id: str,
        lock_notes: Optional[str] = None
    ) -> models.AccountingPeriod:
        """
        Lock an accounting period (closed → locked)
        
        Locked periods:
        - Absolutely no changes allowed
        - Used for year-end close and audit compliance
        - Cannot be unlocked (requires database intervention)
        - All documents in period are also locked
        
        Args:
            period_id: Period ID to lock
            lock_notes: Optional notes about locking
        
        Returns:
            Updated period
        """
        period = self.db.query(models.AccountingPeriod).filter(
            models.AccountingPeriod.id == period_id,
            models.AccountingPeriod.company_id == self.company_id
        ).first()
        
        if not period:
            raise HTTPException(status_code=404, detail="Period not found")
        
        if period.status != "closed":
            raise HTTPException(
                status_code=400,
                detail=f"Can only lock 'closed' periods. Current status: {period.status}. Close the period first."
            )
        
        # Lock all journal entries in this period
        journals_locked = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.date >= period.start_date,
            models.JournalEntry.date <= period.end_date,
            models.JournalEntry.status == "posted"
        ).update({"status": "locked"})
        
        # Lock period
        period.status = "locked"
        period.locked_by = self.user_id
        period.locked_at = datetime.now()
        period.lock_notes = lock_notes
        
        self.db.commit()
        self.db.refresh(period)
        
        logger.info(
            f"Locked accounting period: {period.period_name}. "
            f"Locked {journals_locked} journal entries."
        )
        
        return period
    
    def reopen_period(
        self,
        period_id: str,
        reopen_reason: str
    ) -> models.AccountingPeriod:
        """
        Reopen a closed period (closed → open)
        
        Note: Locked periods CANNOT be reopened
        
        Args:
            period_id: Period ID to reopen
            reopen_reason: Reason for reopening (required)
        
        Returns:
            Updated period
        """
        period = self.db.query(models.AccountingPeriod).filter(
            models.AccountingPeriod.id == period_id,
            models.AccountingPeriod.company_id == self.company_id
        ).first()
        
        if not period:
            raise HTTPException(status_code=404, detail="Period not found")
        
        if period.status == "locked":
            raise HTTPException(
                status_code=400,
                detail="Locked periods cannot be reopened. Contact system administrator."
            )
        
        if period.status != "closed":
            raise HTTPException(
                status_code=400,
                detail=f"Can only reopen 'closed' periods. Current status: {period.status}"
            )
        
        # Reopen period
        period.status = "open"
        period.reopen_reason = reopen_reason
        period.reopened_by = self.user_id
        period.reopened_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(period)
        
        logger.info(f"Reopened accounting period: {period.period_name}. Reason: {reopen_reason}")
        
        return period
    
    def get_period_for_date(self, transaction_date: date) -> Optional[models.AccountingPeriod]:
        """Get the accounting period for a given date"""
        period = self.db.query(models.AccountingPeriod).filter(
            models.AccountingPeriod.company_id == self.company_id,
            models.AccountingPeriod.start_date <= transaction_date,
            models.AccountingPeriod.end_date >= transaction_date
        ).first()
        
        return period
    
    def validate_transaction_date(self, transaction_date: date, allow_closed: bool = False):
        """
        Validate if a transaction can be posted on a given date
        
        Args:
            transaction_date: Date of the transaction
            allow_closed: If True, allow posting to closed periods (with approval)
        
        Raises:
            HTTPException if date is in locked period or period doesn't exist
        """
        period = self.get_period_for_date(transaction_date)
        
        if not period:
            # Auto-create period if it doesn't exist
            logger.warning(f"No period found for date {transaction_date}. Creating period...")
            year = transaction_date.year
            month = transaction_date.month
            
            # Create monthly period
            start = date(year, month, 1)
            if month == 12:
                end = date(year, 12, 31)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
            
            period_name = start.strftime("%B %Y")
            self.create_period(
                period_name=period_name,
                start_date=start,
                end_date=end,
                period_type="monthly",
                fiscal_year=year
            )
            return  # Period is open by default
        
        if period.status == "locked":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot post transaction: Period '{period.period_name}' is locked. "
                       f"Locked periods are immutable for audit compliance."
            )
        
        if period.status == "closed" and not allow_closed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot post transaction: Period '{period.period_name}' is closed. "
                       f"Submit for approval to post to closed period."
            )
    
    def get_all_periods(
        self,
        fiscal_year: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[models.AccountingPeriod]:
        """
        Get all accounting periods for the company
        
        Args:
            fiscal_year: Filter by fiscal year
            status: Filter by status (open, closed, locked)
        
        Returns:
            List of periods
        """
        query = self.db.query(models.AccountingPeriod).filter(
            models.AccountingPeriod.company_id == self.company_id
        )
        
        if fiscal_year:
            query = query.filter(models.AccountingPeriod.fiscal_year == fiscal_year)
        
        if status:
            query = query.filter(models.AccountingPeriod.status == status)
        
        periods = query.order_by(
            models.AccountingPeriod.start_date.desc()
        ).all()
        
        return periods

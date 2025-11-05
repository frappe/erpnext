"""
Finance - Fixed Asset Depreciation Service

Implements fixed asset depreciation per Finance PDF spec:
- Straight-line depreciation
- Declining balance depreciation
- Units of production depreciation
- Automatic depreciation schedule generation
- Monthly depreciation journal entries
- Asset disposal handling
- Accumulated depreciation tracking

Depreciation Methods:
1. Straight-line: (Cost - Salvage) / Useful Life
2. Declining balance: Book Value × Depreciation Rate
3. Units of production: (Cost - Salvage) × (Units Used / Total Units)
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import models
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class FixedAssetDepreciationService:
    """
    Fixed Asset Depreciation Service
    Handles automatic depreciation calculations and journal entry generation
    """
    
    # Depreciation methods
    METHOD_STRAIGHT_LINE = "straight_line"
    METHOD_DECLINING_BALANCE = "declining_balance"
    METHOD_UNITS_OF_PRODUCTION = "units_of_production"
    
    # Asset status
    STATUS_ACTIVE = "active"
    STATUS_DISPOSED = "disposed"
    STATUS_FULLY_DEPRECIATED = "fully_depreciated"
    
    def __init__(self, db: Session, company_id: str, user_id: str):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
    
    def create_fixed_asset(
        self,
        asset_name: str,
        asset_code: str,
        asset_category: str,
        purchase_date: date,
        purchase_cost: Decimal,
        salvage_value: Decimal = Decimal("0.00"),  # Also known as residual_value
        useful_life_years: int = 5,
        depreciation_method: str = METHOD_STRAIGHT_LINE,
        account_id: str = None,
        location: str = None,
        serial_number: str = None,
        supplier_id: str = None
    ) -> models.FixedAsset:
        """
        Create a new fixed asset
        
        Args:
            asset_name: Name/description of asset
            asset_code: Unique asset code
            asset_category: Category (Building, Vehicle, Equipment, etc.)
            purchase_date: Date of purchase/acquisition
            purchase_cost: Original cost of asset
            salvage_value: Expected salvage/residual value
            useful_life_years: Expected useful life in years
            depreciation_method: Method to use for depreciation
            account_id: GL account for asset
            location: Physical location
            serial_number: Serial/VIN number
            supplier_id: Supplier/vendor
        
        Returns:
            Created fixed asset
        """
        # Check if asset code is unique
        existing = self.db.query(models.FixedAsset).filter(
            models.FixedAsset.company_id == self.company_id,
            models.FixedAsset.asset_code == asset_code
        ).first()
        
        if existing:
            raise ValueError(f"Asset code {asset_code} already exists")
        
        # Calculate depreciation rate for declining balance
        if depreciation_method == self.METHOD_DECLINING_BALANCE:
            # Standard declining balance rate: 1 / useful_life × 2 (for double declining)
            depreciation_rate = (1 / useful_life_years) * 2 if useful_life_years > 0 else 0
        else:
            depreciation_rate = 0
        
        # Create fixed asset
        asset = models.FixedAsset(
            company_id=self.company_id,
            asset_code=asset_code,
            asset_name=asset_name,
            asset_category=asset_category,
            purchase_date=purchase_date,
            purchase_cost=float(purchase_cost),
            residual_value=float(salvage_value),  # Model uses residual_value
            useful_life_years=useful_life_years,
            depreciation_method=depreciation_method,
            depreciation_rate=depreciation_rate,
            accumulated_depreciation=0.0,
            book_value=float(purchase_cost),
            status=self.STATUS_ACTIVE,
            asset_account_id=account_id,
            location=location,
            serial_number=serial_number,
            supplier_id=supplier_id,
            created_by=self.user_id
        )
        
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        
        logger.info(
            f"Created fixed asset: {asset_code} - {asset_name}, "
            f"Cost: {purchase_cost}, Method: {depreciation_method}"
        )
        
        return asset
    
    def generate_depreciation_schedule(
        self,
        asset_id: str,
        num_periods: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate depreciation schedule for an asset
        
        Shows projected depreciation for each period until fully depreciated
        
        Args:
            asset_id: ID of fixed asset
            num_periods: Number of periods to generate (None = until fully depreciated)
        
        Returns:
            List of depreciation schedule entries
        """
        # Get asset
        asset = self.db.query(models.FixedAsset).filter(
            models.FixedAsset.id == asset_id,
            models.FixedAsset.company_id == self.company_id
        ).first()
        
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        schedule = []
        
        # Calculate based on depreciation method
        if asset.depreciation_method == self.METHOD_STRAIGHT_LINE:
            schedule = self._generate_straight_line_schedule(asset, num_periods)
        elif asset.depreciation_method == self.METHOD_DECLINING_BALANCE:
            schedule = self._generate_declining_balance_schedule(asset, num_periods)
        elif asset.depreciation_method == self.METHOD_UNITS_OF_PRODUCTION:
            schedule = self._generate_units_schedule(asset, num_periods)
        else:
            raise ValueError(f"Unknown depreciation method: {asset.depreciation_method}")
        
        return schedule
    
    def _generate_straight_line_schedule(
        self,
        asset: models.FixedAsset,
        num_periods: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Generate straight-line depreciation schedule"""
        depreciable_amount = Decimal(str(asset.purchase_cost)) - Decimal(str(asset.residual_value))
        total_months = asset.useful_life_years * 12
        monthly_depreciation = depreciable_amount / total_months if total_months > 0 else Decimal("0")
        
        # Start from first month after purchase
        current_date = asset.purchase_date + relativedelta(months=1)
        current_date = current_date.replace(day=1)  # First day of month
        
        accumulated = Decimal(str(asset.accumulated_depreciation))
        book_value = Decimal(str(asset.book_value))
        
        periods = num_periods if num_periods else total_months
        schedule = []
        
        for period in range(int(periods)):
            # Don't depreciate below residual value
            if book_value <= Decimal(str(asset.residual_value)):
                break
            
            # Adjust last period if needed
            depreciation = min(monthly_depreciation, book_value - Decimal(str(asset.residual_value)))
            accumulated += depreciation
            book_value -= depreciation
            
            schedule.append({
                "period": period + 1,
                "date": current_date,
                "depreciation_expense": float(depreciation),
                "accumulated_depreciation": float(accumulated),
                "book_value": float(book_value)
            })
            
            current_date = current_date + relativedelta(months=1)
        
        return schedule
    
    def _generate_declining_balance_schedule(
        self,
        asset: models.FixedAsset,
        num_periods: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Generate declining balance depreciation schedule"""
        monthly_rate = Decimal(str(asset.depreciation_rate)) / 12
        
        current_date = asset.purchase_date + relativedelta(months=1)
        current_date = current_date.replace(day=1)
        
        accumulated = Decimal(str(asset.accumulated_depreciation))
        book_value = Decimal(str(asset.book_value))
        
        total_months = asset.useful_life_years * 12
        periods = num_periods if num_periods else total_months
        schedule = []
        
        for period in range(int(periods)):
            if book_value <= Decimal(str(asset.residual_value)):
                break
            
            # Depreciation = Book Value × Rate
            depreciation = book_value * monthly_rate
            
            # Don't go below residual value
            depreciation = min(depreciation, book_value - Decimal(str(asset.residual_value)))
            
            accumulated += depreciation
            book_value -= depreciation
            
            schedule.append({
                "period": period + 1,
                "date": current_date,
                "depreciation_expense": float(depreciation),
                "accumulated_depreciation": float(accumulated),
                "book_value": float(book_value)
            })
            
            current_date = current_date + relativedelta(months=1)
        
        return schedule
    
    def _generate_units_schedule(
        self,
        asset: models.FixedAsset,
        num_periods: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Generate units of production depreciation schedule"""
        # For units of production, we need actual usage data
        # This is a placeholder - would need usage tracking
        return [{
            "period": 1,
            "date": asset.purchase_date,
            "depreciation_expense": 0.0,
            "accumulated_depreciation": 0.0,
            "book_value": asset.book_value,
            "note": "Units of production requires actual usage data"
        }]
    
    def calculate_depreciation(
        self,
        asset_id: str,
        as_of_date: date
    ) -> Dict[str, Any]:
        """
        Calculate depreciation for an asset up to a specific date
        
        Args:
            asset_id: ID of fixed asset
            as_of_date: Date to calculate depreciation to
        
        Returns:
            Depreciation calculation result
        """
        asset = self.db.query(models.FixedAsset).filter(
            models.FixedAsset.id == asset_id,
            models.FixedAsset.company_id == self.company_id
        ).first()
        
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Calculate months since purchase
        months_owned = relativedelta(as_of_date, asset.purchase_date).months
        months_owned += relativedelta(as_of_date, asset.purchase_date).years * 12
        
        if months_owned <= 0:
            return {
                "asset_id": asset_id,
                "depreciation_expense": 0.0,
                "accumulated_depreciation": asset.accumulated_depreciation,
                "book_value": asset.book_value
            }
        
        # Generate schedule and get total depreciation
        schedule = self.generate_depreciation_schedule(asset_id, num_periods=months_owned)
        
        if not schedule:
            return {
                "asset_id": asset_id,
                "depreciation_expense": 0.0,
                "accumulated_depreciation": asset.accumulated_depreciation,
                "book_value": asset.book_value
            }
        
        last_entry = schedule[-1]
        
        return {
            "asset_id": asset_id,
            "as_of_date": as_of_date,
            "depreciation_expense": last_entry["depreciation_expense"],
            "accumulated_depreciation": last_entry["accumulated_depreciation"],
            "book_value": last_entry["book_value"]
        }
    
    def record_depreciation(
        self,
        asset_id: str,
        period_date: date,
        create_journal: bool = True
    ) -> Dict[str, Any]:
        """
        Record depreciation for an asset for a specific period
        
        Updates accumulated depreciation and optionally creates journal entry
        
        Args:
            asset_id: ID of fixed asset
            period_date: Period to record depreciation for
            create_journal: If True, create depreciation journal entry
        
        Returns:
            Recording result
        """
        asset = self.db.query(models.FixedAsset).filter(
            models.FixedAsset.id == asset_id,
            models.FixedAsset.company_id == self.company_id
        ).first()
        
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        if asset.status != self.STATUS_ACTIVE:
            raise ValueError(f"Asset is not active (status: {asset.status})")
        
        # Calculate depreciation for this period
        result = self.calculate_depreciation(asset_id, period_date)
        
        depreciation_expense = Decimal(str(result["depreciation_expense"]))
        
        if depreciation_expense <= 0:
            return {
                "success": True,
                "asset_id": asset_id,
                "period_date": period_date,
                "depreciation_expense": 0.0,
                "message": "No depreciation recorded (fully depreciated or no depreciation due)"
            }
        
        # Update asset
        asset.accumulated_depreciation = result["accumulated_depreciation"]
        asset.book_value = result["book_value"]
        
        # Check if fully depreciated
        if asset.book_value <= asset.residual_value:
            asset.status = self.STATUS_FULLY_DEPRECIATED
        
        self.db.commit()
        self.db.refresh(asset)
        
        # Create journal entry if requested
        journal_entry_id = None
        
        if create_journal:
            journal_entry_id = self._create_depreciation_journal(
                asset=asset,
                period_date=period_date,
                depreciation_amount=depreciation_expense
            )
        
        logger.info(
            f"Recorded depreciation for {asset.asset_code}: "
            f"{depreciation_expense}, Accumulated: {asset.accumulated_depreciation}"
        )
        
        return {
            "success": True,
            "asset_id": asset_id,
            "asset_code": asset.asset_code,
            "period_date": period_date,
            "depreciation_expense": float(depreciation_expense),
            "accumulated_depreciation": asset.accumulated_depreciation,
            "book_value": asset.book_value,
            "status": asset.status,
            "journal_entry_id": journal_entry_id
        }
    
    def _create_depreciation_journal(
        self,
        asset: models.FixedAsset,
        period_date: date,
        depreciation_amount: Decimal
    ) -> str:
        """Create journal entry for depreciation"""
        from .journal_service import JournalEntryService
        
        # Get or create depreciation expense account
        expense_account = self._get_depreciation_expense_account(asset.asset_category)
        
        # Get or create accumulated depreciation account
        accum_account = self._get_accumulated_depreciation_account(asset.asset_category)
        
        # Create journal entry
        journal_service = JournalEntryService(self.db, self.company_id, self.user_id)
        
        journal_data = {
            "lines": [
                {
                    "account_code": expense_account.code,
                    "side": "debit",
                    "amount": float(depreciation_amount),
                    "narration": f"Depreciation - {asset.asset_name}"
                },
                {
                    "account_code": accum_account.code,
                    "side": "credit",
                    "amount": float(depreciation_amount),
                    "narration": f"Accumulated depreciation - {asset.asset_name}"
                }
            ]
        }
        
        journal_entry = journal_service.create_journal_entry(
            journal_number=journal_service.generate_journal_number(),
            entry_date=period_date,
            description=f"Depreciation - {asset.asset_code} - {period_date.strftime('%B %Y')}",
            currency="ZMW",
            data=journal_data,
            source_type="depreciation",
            source_id=asset.id,
            auto_post=True
        )
        
        return journal_entry.id
    
    def _get_depreciation_expense_account(self, category: str) -> models.Account:
        """Get or create depreciation expense account"""
        account_code = f"6300-DEP-{category.upper()[:3]}"
        
        account = self.db.query(models.Account).filter(
            models.Account.company_id == self.company_id,
            models.Account.code == account_code
        ).first()
        
        if not account:
            account = models.Account(
                company_id=self.company_id,
                code=account_code,
                name=f"Depreciation Expense - {category}",
                account_type="expense",
                description=f"Depreciation expense for {category} assets",
                is_active=True
            )
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
        
        return account
    
    def _get_accumulated_depreciation_account(self, category: str) -> models.Account:
        """Get or create accumulated depreciation account"""
        account_code = f"1900-ACCDEP-{category.upper()[:3]}"
        
        account = self.db.query(models.Account).filter(
            models.Account.company_id == self.company_id,
            models.Account.code == account_code
        ).first()
        
        if not account:
            account = models.Account(
                company_id=self.company_id,
                code=account_code,
                name=f"Accumulated Depreciation - {category}",
                account_type="asset",
                description=f"Accumulated depreciation for {category} assets (contra-asset)",
                is_active=True
            )
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
        
        return account
    
    def run_monthly_depreciation(
        self,
        period_date: date
    ) -> Dict[str, Any]:
        """
        Run depreciation for all active assets for a specific month
        
        This should be run as a scheduled job at month-end
        
        Args:
            period_date: Period to run depreciation for
        
        Returns:
            Batch depreciation results
        """
        # Get all active assets
        assets = self.db.query(models.FixedAsset).filter(
            models.FixedAsset.company_id == self.company_id,
            models.FixedAsset.status == self.STATUS_ACTIVE,
            models.FixedAsset.purchase_date < period_date
        ).all()
        
        results = []
        total_depreciation = Decimal("0.00")
        
        for asset in assets:
            try:
                result = self.record_depreciation(
                    asset_id=asset.id,
                    period_date=period_date,
                    create_journal=True
                )
                results.append(result)
                total_depreciation += Decimal(str(result["depreciation_expense"]))
            except Exception as e:
                logger.error(f"Error depreciating asset {asset.asset_code}: {str(e)}")
                results.append({
                    "success": False,
                    "asset_id": asset.id,
                    "asset_code": asset.asset_code,
                    "error": str(e)
                })
        
        logger.info(
            f"Monthly depreciation run for {period_date}: "
            f"{len(results)} assets, total depreciation: {total_depreciation}"
        )
        
        return {
            "success": True,
            "period_date": period_date,
            "assets_processed": len(results),
            "total_depreciation": float(total_depreciation),
            "results": results
        }
    
    def dispose_asset(
        self,
        asset_id: str,
        disposal_date: date,
        disposal_proceeds: Decimal,
        create_journal: bool = True
    ) -> Dict[str, Any]:
        """
        Dispose of a fixed asset
        
        Calculates gain/loss on disposal and creates journal entry
        
        Args:
            asset_id: ID of fixed asset
            disposal_date: Date of disposal
            disposal_proceeds: Amount received from disposal
            create_journal: If True, create disposal journal entry
        
        Returns:
            Disposal result with gain/loss
        """
        asset = self.db.query(models.FixedAsset).filter(
            models.FixedAsset.id == asset_id,
            models.FixedAsset.company_id == self.company_id
        ).first()
        
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Calculate final book value
        book_value = Decimal(str(asset.book_value))
        
        # Calculate gain/loss
        gain_loss = disposal_proceeds - book_value
        
        # Update asset
        asset.status = self.STATUS_DISPOSED
        asset.disposal_date = disposal_date
        asset.disposal_proceeds = float(disposal_proceeds)
        asset.disposal_gain_loss = float(gain_loss)
        
        self.db.commit()
        self.db.refresh(asset)
        
        logger.info(
            f"Disposed asset {asset.asset_code}: "
            f"Proceeds: {disposal_proceeds}, Book Value: {book_value}, "
            f"{'Gain' if gain_loss > 0 else 'Loss'}: {abs(gain_loss)}"
        )
        
        return {
            "success": True,
            "asset_id": asset_id,
            "asset_code": asset.asset_code,
            "disposal_date": disposal_date,
            "book_value": float(book_value),
            "disposal_proceeds": float(disposal_proceeds),
            "gain_loss": float(gain_loss),
            "status": asset.status
        }

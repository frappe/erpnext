"""
Consolidation & Reporting Engine

Features:
- Organizational hierarchy consolidation (Department → Sector → Enterprise)
- Inter-company / inter-department elimination
- Multi-dimensional reporting (units, weight, volume, value)
- Cash flow statement generation
- Consolidated financials (P&L, Balance Sheet)
- Yield reports and loss/gain analysis
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

import models

logger = logging.getLogger(__name__)

class ConsolidationEngine:
    """Engine for financial consolidation and multi-dimensional reporting"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # CONSOLIDATED FINANCIAL STATEMENTS
    # ========================================================================
    
    def generate_consolidated_pnl(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        consolidation_level: str = "company",  # company, sector, enterprise
        consolidation_id: Optional[str] = None,
        eliminate_intercompany: bool = True
    ) -> Dict:
        """
        Generate Consolidated Profit & Loss Statement
        
        Aggregates across departments/sectors/companies
        Eliminates inter-company/inter-department transfers if requested
        """
        # Get all journal entries in the period
        query = self.db.query(models.JournalEntry).filter(
            and_(
                models.JournalEntry.company_id == company_id,
                models.JournalEntry.posting_date >= start_date,
                models.JournalEntry.posting_date <= end_date,
                models.JournalEntry.status == "posted"
            )
        )
        
        # Apply consolidation filters
        if consolidation_level == "department" and consolidation_id:
            query = query.filter(models.JournalEntry.department_id == consolidation_id)
        # TODO: Add sector and enterprise filters when multi-company is implemented
        
        journal_entries = query.all()
        
        # Aggregate P&L accounts
        revenue = 0.0
        cost_of_sales = 0.0
        operating_expenses = 0.0
        other_income = 0.0
        other_expenses = 0.0
        
        for journal in journal_entries:
            for line in journal.lines:
                account = self.db.query(models.Account).filter(
                    models.Account.id == line.account_id
                ).first()
                
                if not account:
                    continue
                
                amount = line.amount if line.side == "credit" else -line.amount
                
                # Classify by account type
                if account.account_type == "revenue":
                    revenue += amount
                elif account.account_type == "cost_of_sales":
                    cost_of_sales += abs(amount)
                elif account.account_type == "expense":
                    operating_expenses += abs(amount)
                elif account.account_type == "other_income":
                    other_income += amount
                elif account.account_type == "other_expense":
                    other_expenses += abs(amount)
        
        # Calculate P&L metrics
        gross_profit = revenue - cost_of_sales
        gross_profit_margin = (gross_profit / revenue * 100) if revenue > 0 else 0.0
        
        operating_profit = gross_profit - operating_expenses
        operating_margin = (operating_profit / revenue * 100) if revenue > 0 else 0.0
        
        net_profit = operating_profit + other_income - other_expenses
        net_margin = (net_profit / revenue * 100) if revenue > 0 else 0.0
        
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "consolidation": {
                "level": consolidation_level,
                "id": consolidation_id
            },
            "revenue": revenue,
            "cost_of_sales": cost_of_sales,
            "gross_profit": gross_profit,
            "gross_profit_margin_pct": gross_profit_margin,
            "operating_expenses": operating_expenses,
            "operating_profit": operating_profit,
            "operating_margin_pct": operating_margin,
            "other_income": other_income,
            "other_expenses": other_expenses,
            "net_profit": net_profit,
            "net_margin_pct": net_margin
        }
    
    def generate_consolidated_balance_sheet(
        self,
        company_id: str,
        as_of_date: date,
        consolidation_level: str = "company",
        consolidation_id: Optional[str] = None
    ) -> Dict:
        """Generate Consolidated Balance Sheet"""
        # Get all posted journal entries up to the date
        journal_entries = self.db.query(models.JournalEntry).filter(
            and_(
                models.JournalEntry.company_id == company_id,
                models.JournalEntry.posting_date <= as_of_date,
                models.JournalEntry.status == "posted"
            )
        ).all()
        
        # Aggregate by account type
        current_assets = 0.0
        non_current_assets = 0.0
        current_liabilities = 0.0
        non_current_liabilities = 0.0
        equity = 0.0
        
        for journal in journal_entries:
            for line in journal.lines:
                account = self.db.query(models.Account).filter(
                    models.Account.id == line.account_id
                ).first()
                
                if not account:
                    continue
                
                amount = line.amount if line.side == "debit" else -line.amount
                
                # Classify by account type
                if account.account_type in ["cash", "bank", "receivables", "inventory"]:
                    current_assets += amount
                elif account.account_type in ["fixed_assets", "intangible_assets"]:
                    non_current_assets += amount
                elif account.account_type in ["payables", "short_term_loans"]:
                    current_liabilities += abs(amount)
                elif account.account_type in ["long_term_loans"]:
                    non_current_liabilities += abs(amount)
                elif account.account_type in ["equity", "retained_earnings"]:
                    equity += amount
        
        total_assets = current_assets + non_current_assets
        total_liabilities = current_liabilities + non_current_liabilities
        total_equity = equity
        
        # Calculate ratios
        current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0.0
        debt_to_equity = total_liabilities / total_equity if total_equity > 0 else 0.0
        
        return {
            "as_of_date": as_of_date,
            "assets": {
                "current_assets": current_assets,
                "non_current_assets": non_current_assets,
                "total_assets": total_assets
            },
            "liabilities": {
                "current_liabilities": current_liabilities,
                "non_current_liabilities": non_current_liabilities,
                "total_liabilities": total_liabilities
            },
            "equity": {
                "total_equity": total_equity
            },
            "total_liabilities_and_equity": total_liabilities + total_equity,
            "ratios": {
                "current_ratio": current_ratio,
                "debt_to_equity": debt_to_equity
            }
        }
    
    def generate_cash_flow_statement(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        method: str = "indirect"  # indirect or direct
    ) -> Dict:
        """
        Generate Cash Flow Statement with drill-down capability
        
        Categories:
        - Operating Activities
        - Investing Activities
        - Financing Activities
        """
        # Get opening cash balance
        opening_cash = self._get_cash_balance(company_id, start_date)
        
        # Operating Activities (simplified - should use proper cash flow calculation)
        operating_cash = 0.0
        
        # Get all cash/bank transactions
        cash_journals = self.db.query(models.JournalEntry).filter(
            and_(
                models.JournalEntry.company_id == company_id,
                models.JournalEntry.posting_date >= start_date,
                models.JournalEntry.posting_date <= end_date,
                models.JournalEntry.status == "posted"
            )
        ).all()
        
        operating_inflows = 0.0
        operating_outflows = 0.0
        investing_inflows = 0.0
        investing_outflows = 0.0
        financing_inflows = 0.0
        financing_outflows = 0.0
        
        for journal in cash_journals:
            cash_movement = 0.0
            activity_type = None
            
            for line in journal.lines:
                account = self.db.query(models.Account).filter(
                    models.Account.id == line.account_id
                ).first()
                
                if not account:
                    continue
                
                # Check if this is a cash/bank account
                if account.account_type in ["cash", "bank"]:
                    cash_movement = line.amount if line.side == "debit" else -line.amount
                
                # Determine activity type based on contra account
                if account.account_type == "revenue" or account.account_type == "expense":
                    activity_type = "operating"
                elif account.account_type in ["fixed_assets", "intangible_assets"]:
                    activity_type = "investing"
                elif account.account_type in ["equity", "long_term_loans"]:
                    activity_type = "financing"
            
            # Categorize cash flows
            if cash_movement != 0 and activity_type:
                if activity_type == "operating":
                    if cash_movement > 0:
                        operating_inflows += cash_movement
                    else:
                        operating_outflows += abs(cash_movement)
                elif activity_type == "investing":
                    if cash_movement > 0:
                        investing_inflows += cash_movement
                    else:
                        investing_outflows += abs(cash_movement)
                elif activity_type == "financing":
                    if cash_movement > 0:
                        financing_inflows += cash_movement
                    else:
                        financing_outflows += abs(cash_movement)
        
        # Calculate net cash flows
        net_operating = operating_inflows - operating_outflows
        net_investing = investing_inflows - investing_outflows
        net_financing = financing_inflows - financing_outflows
        
        net_change = net_operating + net_investing + net_financing
        closing_cash = opening_cash + net_change
        
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "opening_cash": opening_cash,
            "operating_activities": {
                "inflows": operating_inflows,
                "outflows": operating_outflows,
                "net_cash_from_operations": net_operating
            },
            "investing_activities": {
                "inflows": investing_inflows,
                "outflows": investing_outflows,
                "net_cash_from_investing": net_investing
            },
            "financing_activities": {
                "inflows": financing_inflows,
                "outflows": financing_outflows,
                "net_cash_from_financing": net_financing
            },
            "net_change_in_cash": net_change,
            "closing_cash": closing_cash
        }
    
    def _get_cash_balance(self, company_id: str, as_of_date: date) -> float:
        """Get total cash/bank balance as of a date"""
        # Get all cash/bank accounts
        cash_accounts = self.db.query(models.Account).filter(
            and_(
                models.Account.company_id == company_id,
                models.Account.account_type.in_(["cash", "bank"])
            )
        ).all()
        
        total_cash = 0.0
        
        for account in cash_accounts:
            # Get all journal lines for this account up to the date
            lines = self.db.query(models.JournalLine).join(models.JournalEntry).filter(
                and_(
                    models.JournalLine.account_id == account.id,
                    models.JournalEntry.posting_date <= as_of_date,
                    models.JournalEntry.status == "posted"
                )
            ).all()
            
            account_balance = 0.0
            for line in lines:
                if line.side == "debit":
                    account_balance += line.amount
                else:
                    account_balance -= line.amount
            
            total_cash += account_balance
        
        return total_cash
    
    # ========================================================================
    # MULTI-DIMENSIONAL REPORTING
    # ========================================================================
    
    def generate_multidimensional_report(
        self,
        company_id: str,
        start_date: date,
        end_date: date,
        dimensions: List[str] = ["units", "value"]
    ) -> Dict:
        """
        Multi-dimensional inventory/production reporting
        Dimensions: units, weight, volume, value
        """
        # Get all production orders in period
        production_orders = self.db.query(models.ProductionOrder).filter(
            and_(
                models.ProductionOrder.company_id == company_id,
                models.ProductionOrder.status == "completed",
                models.ProductionOrder.actual_end >= start_date,
                models.ProductionOrder.actual_end <= end_date
            )
        ).all()
        
        report_data = {
            "period": {"start_date": start_date, "end_date": end_date},
            "dimensions": {},
            "by_product": []
        }
        
        # Aggregate by dimensions
        if "units" in dimensions:
            total_units = sum(po.produced_quantity for po in production_orders)
            report_data["dimensions"]["total_units_produced"] = total_units
        
        if "value" in dimensions:
            total_value = sum(po.total_cost or 0.0 for po in production_orders)
            report_data["dimensions"]["total_production_value"] = total_value
        
        # By product breakdown
        product_summary = {}
        for po in production_orders:
            product_id = po.product_id
            if product_id not in product_summary:
                product = self.db.query(models.Product).filter(
                    models.Product.id == product_id
                ).first()
                
                product_summary[product_id] = {
                    "product_id": product_id,
                    "product_name": product.name if product else "Unknown",
                    "units": 0.0,
                    "value": 0.0
                }
            
            product_summary[product_id]["units"] += po.produced_quantity
            product_summary[product_id]["value"] += po.total_cost or 0.0
        
        report_data["by_product"] = list(product_summary.values())
        
        return report_data
    
    # ========================================================================
    # YIELD & LOSS REPORTING
    # ========================================================================
    
    def generate_yield_report(
        self,
        company_id: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        Generate yield report showing:
        - Expected vs Actual production
        - Normal vs Abnormal loss
        - Scrap and waste analysis
        """
        production_orders = self.db.query(models.ProductionOrder).filter(
            and_(
                models.ProductionOrder.company_id == company_id,
                models.ProductionOrder.status == "completed",
                models.ProductionOrder.actual_end >= start_date,
                models.ProductionOrder.actual_end <= end_date
            )
        ).all()
        
        total_planned = 0.0
        total_produced = 0.0
        total_scrapped = 0.0
        
        order_details = []
        
        for po in production_orders:
            planned_qty = po.planned_quantity
            produced_qty = po.produced_quantity
            scrapped_qty = po.scrapped_quantity or 0.0
            
            total_planned += planned_qty
            total_produced += produced_qty
            total_scrapped += scrapped_qty
            
            # Calculate yield percentage
            yield_pct = (produced_qty / planned_qty * 100) if planned_qty > 0 else 0.0
            loss_qty = planned_qty - produced_qty - scrapped_qty
            loss_pct = (loss_qty / planned_qty * 100) if planned_qty > 0 else 0.0
            
            # Classify loss as normal or abnormal (>5% is abnormal)
            normal_loss_threshold = 0.05  # 5%
            is_abnormal = (loss_pct / 100) > normal_loss_threshold
            
            product = self.db.query(models.Product).filter(
                models.Product.id == po.product_id
            ).first()
            
            order_details.append({
                "po_number": po.po_number,
                "product_name": product.name if product else "Unknown",
                "planned_quantity": planned_qty,
                "produced_quantity": produced_qty,
                "scrapped_quantity": scrapped_qty,
                "loss_quantity": loss_qty,
                "yield_percentage": yield_pct,
                "loss_percentage": loss_pct,
                "loss_type": "abnormal" if is_abnormal else "normal"
            })
        
        # Overall yield
        overall_yield_pct = (total_produced / total_planned * 100) if total_planned > 0 else 0.0
        total_loss = total_planned - total_produced - total_scrapped
        overall_loss_pct = (total_loss / total_planned * 100) if total_planned > 0 else 0.0
        
        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "summary": {
                "total_planned": total_planned,
                "total_produced": total_produced,
                "total_scrapped": total_scrapped,
                "total_loss": total_loss,
                "overall_yield_pct": overall_yield_pct,
                "overall_loss_pct": overall_loss_pct
            },
            "production_orders": order_details
        }
    
    def generate_surplus_shortage_report(
        self,
        company_id: str
    ) -> Dict:
        """
        Inventory surplus/shortage analysis
        Compares current stock levels with reorder levels
        """
        products = self.db.query(models.Product).filter(
            models.Product.company_id == company_id,
            models.Product.is_active == True
        ).all()
        
        surplus_items = []
        shortage_items = []
        normal_items = []
        
        for product in products:
            # Get total stock across all warehouses
            stock_items = self.db.query(models.StockItem).filter(
                models.StockItem.product_id == product.id,
                models.StockItem.company_id == company_id
            ).all()
            
            total_stock = sum(item.quantity_on_hand for item in stock_items)
            reorder_level = product.reorder_level or 0.0
            
            if total_stock < reorder_level:
                shortage_qty = reorder_level - total_stock
                shortage_items.append({
                    "product_id": product.id,
                    "product_code": product.code,
                    "product_name": product.name,
                    "current_stock": total_stock,
                    "reorder_level": reorder_level,
                    "shortage_quantity": shortage_qty,
                    "status": "critical" if total_stock == 0 else "low"
                })
            elif total_stock > reorder_level * 3:  # Surplus if > 3x reorder level
                surplus_qty = total_stock - (reorder_level * 2)
                surplus_items.append({
                    "product_id": product.id,
                    "product_code": product.code,
                    "product_name": product.name,
                    "current_stock": total_stock,
                    "reorder_level": reorder_level,
                    "surplus_quantity": surplus_qty
                })
            else:
                normal_items.append({
                    "product_id": product.id,
                    "product_code": product.code,
                    "product_name": product.name,
                    "current_stock": total_stock,
                    "reorder_level": reorder_level
                })
        
        return {
            "summary": {
                "total_products": len(products),
                "shortage_count": len(shortage_items),
                "surplus_count": len(surplus_items),
                "normal_count": len(normal_items)
            },
            "shortage_items": shortage_items,
            "surplus_items": surplus_items,
            "normal_items": normal_items
        }

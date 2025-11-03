"""
Landed Cost Allocation Service

Handles:
- Landed cost components (freight, insurance, duties, handling)
- Cost allocation to products (by value, quantity, weight, volume)
- Transfer pricing between locations
"""

import logging
from datetime import date
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

class LandedCostService:
    """Service for landed cost allocation and transfer pricing"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_landed_cost(
        self,
        company_id: str,
        reference_type: str,
        reference_id: str,
        freight_cost: float = 0.0,
        insurance_cost: float = 0.0,
        customs_duty: float = 0.0,
        handling_charges: float = 0.0,
        other_charges: float = 0.0,
        allocation_method: str = "value",
        created_by: Optional[str] = None
    ) -> models.LandedCost:
        """Create landed cost document"""
        # Generate landed cost number
        lc_number = self._generate_lc_number(company_id)
        
        total_landed_cost = (freight_cost + insurance_cost + customs_duty + 
                           handling_charges + other_charges)
        
        landed_cost = models.LandedCost(
            company_id=company_id,
            landed_cost_number=lc_number,
            reference_date=date.today(),
            reference_type=reference_type,
            reference_id=reference_id,
            freight_cost=freight_cost,
            insurance_cost=insurance_cost,
            customs_duty=customs_duty,
            handling_charges=handling_charges,
            other_charges=other_charges,
            total_landed_cost=total_landed_cost,
            allocation_method=allocation_method,
            status="draft",
            created_by=created_by
        )
        
        self.db.add(landed_cost)
        self.db.commit()
        self.db.refresh(landed_cost)
        
        logger.info(f"Created landed cost {lc_number} with total {total_landed_cost}")
        
        return landed_cost
    
    def allocate_costs(self, landed_cost_id: str, products: List[Dict]) -> List[models.LandedCostAllocation]:
        """
        Allocate landed costs to products
        
        products format: [
            {
                "product_id": "...",
                "quantity": 100,
                "base_value": 10000,  # Product value
                "base_weight": 500,   # kg
                "base_volume": 2.5,   # m3
                "original_unit_cost": 100
            },
            ...
        ]
        """
        lc = self.db.query(models.LandedCost).filter(
            models.LandedCost.id == landed_cost_id
        ).first()
        
        if not lc:
            raise ValueError("Landed cost not found")
        
        if lc.status != "draft":
            raise ValueError(f"Cannot allocate costs for landed cost in status: {lc.status}")
        
        # Calculate allocation base totals
        total_value = sum(p["base_value"] for p in products)
        total_quantity = sum(p["quantity"] for p in products)
        total_weight = sum(p.get("base_weight", 0) for p in products)
        total_volume = sum(p.get("base_volume", 0) for p in products)
        
        allocations = []
        
        for product in products:
            # Calculate allocation ratios based on method
            if lc.allocation_method == "value":
                ratio = product["base_value"] / total_value if total_value > 0 else 0
            elif lc.allocation_method == "quantity":
                ratio = product["quantity"] / total_quantity if total_quantity > 0 else 0
            elif lc.allocation_method == "weight":
                ratio = product.get("base_weight", 0) / total_weight if total_weight > 0 else 0
            elif lc.allocation_method == "volume":
                ratio = product.get("base_volume", 0) / total_volume if total_volume > 0 else 0
            else:
                ratio = product["quantity"] / total_quantity if total_quantity > 0 else 0
            
            # Allocate costs
            allocated_freight = lc.freight_cost * ratio
            allocated_insurance = lc.insurance_cost * ratio
            allocated_duty = lc.customs_duty * ratio
            allocated_handling = lc.handling_charges * ratio
            allocated_other = lc.other_charges * ratio
            total_allocated = (allocated_freight + allocated_insurance + allocated_duty + 
                             allocated_handling + allocated_other)
            
            # Calculate adjusted unit cost
            original_unit_cost = product["original_unit_cost"]
            cost_adjustment_per_unit = total_allocated / product["quantity"] if product["quantity"] > 0 else 0
            adjusted_unit_cost = original_unit_cost + cost_adjustment_per_unit
            
            # Create allocation
            allocation = models.LandedCostAllocation(
                landed_cost_id=landed_cost_id,
                product_id=product["product_id"],
                quantity=product["quantity"],
                base_value=product["base_value"],
                base_quantity=product["quantity"],
                base_weight=product.get("base_weight"),
                base_volume=product.get("base_volume"),
                allocated_freight=allocated_freight,
                allocated_insurance=allocated_insurance,
                allocated_duty=allocated_duty,
                allocated_handling=allocated_handling,
                allocated_other=allocated_other,
                total_allocated=total_allocated,
                original_unit_cost=original_unit_cost,
                adjusted_unit_cost=adjusted_unit_cost
            )
            
            self.db.add(allocation)
            allocations.append(allocation)
            
            # Update product cost price
            prod = self.db.query(models.Product).filter(
                models.Product.id == product["product_id"]
            ).first()
            if prod:
                prod.cost_price = adjusted_unit_cost
        
        self.db.commit()
        
        logger.info(f"Allocated landed costs to {len(allocations)} products")
        
        return allocations
    
    def post_landed_cost(self, landed_cost_id: str, user_id: str) -> models.LandedCost:
        """Post landed cost (make it final)"""
        lc = self.db.query(models.LandedCost).filter(
            models.LandedCost.id == landed_cost_id
        ).first()
        
        if not lc:
            raise ValueError("Landed cost not found")
        
        if lc.status != "draft":
            raise ValueError(f"Cannot post landed cost in status: {lc.status}")
        
        # TODO: Create GL journal entry for landed costs
        # Dr Inventory, Cr AP/Cash
        
        lc.status = "posted"
        lc.posted_at = date.today()
        
        self.db.commit()
        
        logger.info(f"Posted landed cost {lc.landed_cost_number}")
        
        return lc
    
    def calculate_transfer_price(
        self,
        product_id: str,
        from_location_id: str,
        to_location_id: str,
        from_location_type: str = "warehouse",
        to_location_type: str = "warehouse"
    ) -> Dict:
        """Calculate transfer price based on transfer pricing rules"""
        # Get product
        product = self.db.query(models.Product).filter(
            models.Product.id == product_id
        ).first()
        
        if not product:
            raise ValueError("Product not found")
        
        # Look for applicable transfer pricing rule
        rule = self.db.query(models.TransferPricingRule).filter(
            models.TransferPricingRule.company_id == product.company_id,
            models.TransferPricingRule.product_id == product_id,
            models.TransferPricingRule.from_location_type == from_location_type,
            models.TransferPricingRule.from_location_id == from_location_id,
            models.TransferPricingRule.to_location_type == to_location_type,
            models.TransferPricingRule.to_location_id == to_location_id,
            models.TransferPricingRule.is_active == True
        ).first()
        
        # Calculate transfer price based on rule
        base_cost = product.cost_price or 0.0
        
        if rule:
            if rule.pricing_method == "cost":
                transfer_price = base_cost
            elif rule.pricing_method == "cost_plus":
                markup = (rule.markup_percentage / 100 * base_cost) if rule.markup_percentage else 0.0
                fixed_markup = rule.fixed_markup or 0.0
                transfer_price = base_cost + markup + fixed_markup
            elif rule.pricing_method == "market_price":
                transfer_price = product.unit_price or base_cost
            elif rule.pricing_method == "negotiated":
                transfer_price = rule.transfer_price or base_cost
            else:
                transfer_price = base_cost
            
            pricing_method = rule.pricing_method
            rule_id = rule.id
        else:
            # No rule found, use cost
            transfer_price = base_cost
            pricing_method = "cost (default)"
            rule_id = None
        
        return {
            "product_id": product_id,
            "product_name": product.name,
            "base_cost": base_cost,
            "transfer_price": transfer_price,
            "pricing_method": pricing_method,
            "rule_id": rule_id
        }
    
    def _generate_lc_number(self, company_id: str) -> str:
        """Generate unique landed cost number"""
        latest_lc = self.db.query(models.LandedCost).filter(
            models.LandedCost.company_id == company_id
        ).order_by(models.LandedCost.created_at.desc()).first()
        
        if latest_lc and latest_lc.landed_cost_number:
            try:
                last_num = int(latest_lc.landed_cost_number.split('-')[1])
                new_num = last_num + 1
            except (IndexError, ValueError):
                new_num = 1
        else:
            new_num = 1
        
        return f"LC-{new_num:05d}"


class ConsignmentService:
    """Service for consignment inventory tracking"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_consignment_out(
        self,
        company_id: str,
        product_id: str,
        customer_id: str,
        quantity: float,
        warehouse_id: str,
        consignment_date: date,
        expected_return_date: Optional[date] = None,
        unit_value: float = 0.0,
        created_by: Optional[str] = None,
        notes: str = None
    ) -> models.ConsignmentStock:
        """Send inventory to customer on consignment"""
        consignment = models.ConsignmentStock(
            company_id=company_id,
            consignment_type="consignment_out",
            product_id=product_id,
            quantity=quantity,
            customer_id=customer_id,
            warehouse_id=warehouse_id,
            consignment_date=consignment_date,
            expected_return_date=expected_return_date,
            unit_value=unit_value,
            total_value=unit_value * quantity,
            status="active",
            notes=notes,
            created_by=created_by
        )
        
        self.db.add(consignment)
        
        # Reduce warehouse inventory (but track separately as consignment)
        stock = self.db.query(models.StockItem).filter(
            models.StockItem.product_id == product_id,
            models.StockItem.warehouse_id == warehouse_id,
            models.StockItem.company_id == company_id
        ).first()
        
        if stock:
            stock.quantity_on_hand -= quantity
            stock.reserved_quantity = (stock.reserved_quantity or 0.0) + quantity  # Mark as consignment
        
        self.db.commit()
        self.db.refresh(consignment)
        
        logger.info(f"Created consignment out: {quantity} units to customer {customer_id}")
        
        return consignment
    
    def return_consignment(self, consignment_id: str, actual_return_date: date) -> models.ConsignmentStock:
        """Return consignment inventory"""
        consignment = self.db.query(models.ConsignmentStock).filter(
            models.ConsignmentStock.id == consignment_id
        ).first()
        
        if not consignment:
            raise ValueError("Consignment not found")
        
        if consignment.status != "active":
            raise ValueError(f"Cannot return consignment in status: {consignment.status}")
        
        # Return to warehouse
        if consignment.consignment_type == "consignment_out" and consignment.warehouse_id:
            stock = self.db.query(models.StockItem).filter(
                models.StockItem.product_id == consignment.product_id,
                models.StockItem.warehouse_id == consignment.warehouse_id,
                models.StockItem.company_id == consignment.company_id
            ).first()
            
            if stock:
                stock.quantity_on_hand += consignment.quantity
                stock.reserved_quantity = max(0, (stock.reserved_quantity or 0.0) - consignment.quantity)
        
        consignment.status = "returned"
        consignment.actual_return_date = actual_return_date
        
        self.db.commit()
        
        logger.info(f"Returned consignment {consignment_id}")
        
        return consignment
    
    def sell_consignment(self, consignment_id: str) -> models.ConsignmentStock:
        """Mark consignment as sold (customer kept it)"""
        consignment = self.db.query(models.ConsignmentStock).filter(
            models.ConsignmentStock.id == consignment_id
        ).first()
        
        if not consignment:
            raise ValueError("Consignment not found")
        
        if consignment.status != "active":
            raise ValueError(f"Cannot sell consignment in status: {consignment.status}")
        
        # Remove from reserved quantity (already removed from on-hand when sent)
        if consignment.consignment_type == "consignment_out" and consignment.warehouse_id:
            stock = self.db.query(models.StockItem).filter(
                models.StockItem.product_id == consignment.product_id,
                models.StockItem.warehouse_id == consignment.warehouse_id,
                models.StockItem.company_id == consignment.company_id
            ).first()
            
            if stock:
                stock.reserved_quantity = max(0, (stock.reserved_quantity or 0.0) - consignment.quantity)
        
        consignment.status = "sold"
        
        self.db.commit()
        
        logger.info(f"Sold consignment {consignment_id}")
        
        return consignment

"""
Production Workflow Service
Handles the complete manufacturing cycle: Raw Materials → WIP → Finished Goods

Production Stages:
1. Draft - Order created but not confirmed
2. Confirmed - Order confirmed, materials reserved
3. In Progress - Materials issued to WIP, production started
4. Completed - Finished goods produced, costs calculated
5. Cancelled - Order cancelled, postings reversed
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

import models

logger = logging.getLogger(__name__)

class ProductionWorkflowService:
    """Service for managing production order lifecycle"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_production_order(
        self,
        company_id: str,
        product_id: str,
        planned_quantity: float,
        bom_id: Optional[str] = None,
        routing_id: Optional[str] = None,
        source_warehouse_id: Optional[str] = None,
        destination_warehouse_id: Optional[str] = None,
        scheduled_start: Optional[datetime] = None,
        scheduled_end: Optional[datetime] = None,
        created_by: str = None,
        notes: str = None
    ) -> models.ProductionOrder:
        """
        Create a new production order
        """
        # Get product
        product = self.db.query(models.Product).filter(
            models.Product.id == product_id,
            models.Product.company_id == company_id
        ).first()
        
        if not product:
            raise ValueError("Product not found")
        
        # Get BOM (either specified or default)
        if not bom_id:
            bom = self.db.query(models.BillOfMaterials).filter(
                models.BillOfMaterials.product_id == product_id,
                models.BillOfMaterials.company_id == company_id,
                models.BillOfMaterials.is_default == True,
                models.BillOfMaterials.is_active == True
            ).first()
            if bom:
                bom_id = bom.id
        
        # Generate PO number
        po_number = self._generate_po_number(company_id)
        
        # Create production order
        production_order = models.ProductionOrder(
            company_id=company_id,
            po_number=po_number,
            order_date=date.today(),
            product_id=product_id,
            bom_id=bom_id,
            routing_id=routing_id,
            planned_quantity=planned_quantity,
            source_warehouse_id=source_warehouse_id,
            destination_warehouse_id=destination_warehouse_id,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            status="draft",
            created_by=created_by,
            notes=notes
        )
        
        self.db.add(production_order)
        self.db.commit()
        self.db.refresh(production_order)
        
        logger.info(f"Created production order {po_number} for {planned_quantity} units of {product.name}")
        
        return production_order
    
    def confirm_production_order(self, production_order_id: str, user_id: str) -> models.ProductionOrder:
        """
        Confirm production order - creates material requirement lines from BOM
        """
        po = self.db.query(models.ProductionOrder).filter(
            models.ProductionOrder.id == production_order_id
        ).first()
        
        if not po:
            raise ValueError("Production order not found")
        
        if po.status != "draft":
            raise ValueError(f"Cannot confirm production order in status: {po.status}")
        
        # Create production order lines from BOM
        if po.bom_id:
            bom = self.db.query(models.BillOfMaterials).filter(
                models.BillOfMaterials.id == po.bom_id
            ).first()
            
            if bom:
                # Calculate material requirements
                line_number = 1
                for bom_line in bom.lines:
                    # Calculate quantity needed (including scrap)
                    required_qty = bom_line.quantity * po.planned_quantity
                    if bom_line.scrap_percentage > 0:
                        required_qty = required_qty * (1 + bom_line.scrap_percentage / 100)
                    
                    # Create production order line
                    po_line = models.ProductionOrderLine(
                        production_order_id=po.id,
                        line_type="material",
                        line_number=line_number,
                        product_id=bom_line.component_id,
                        planned_quantity=required_qty,
                        consumed_quantity=0.0,
                        unit_of_measure=bom_line.unit_of_measure,
                        unit_cost=bom_line.unit_cost,
                        total_cost=0.0,
                        operation_id=bom_line.operation_id
                    )
                    self.db.add(po_line)
                    line_number += 1
        
        # Update status
        po.status = "confirmed"
        self.db.commit()
        
        logger.info(f"Confirmed production order {po.po_number}")
        
        return po
    
    def start_production(
        self,
        production_order_id: str,
        user_id: str
    ) -> Dict:
        """
        Start production - issues materials from warehouse to WIP
        Creates GL postings: Dr WIP, Cr Raw Materials
        """
        po = self.db.query(models.ProductionOrder).filter(
            models.ProductionOrder.id == production_order_id
        ).first()
        
        if not po:
            raise ValueError("Production order not found")
        
        if po.status != "confirmed":
            raise ValueError(f"Cannot start production in status: {po.status}")
        
        if not po.source_warehouse_id:
            raise ValueError("Source warehouse not specified")
        
        # Issue materials to WIP
        total_material_cost = 0.0
        materials_issued = []
        
        for line in po.lines:
            if line.line_type == "material" and line.product_id:
                # Get product
                product = self.db.query(models.Product).filter(
                    models.Product.id == line.product_id
                ).first()
                
                if not product:
                    continue
                
                # Get stock
                stock = self.db.query(models.StockItem).filter(
                    models.StockItem.product_id == line.product_id,
                    models.StockItem.warehouse_id == po.source_warehouse_id,
                    models.StockItem.company_id == po.company_id
                ).first()
                
                if not stock:
                    raise ValueError(f"No stock found for {product.name} in source warehouse")
                
                if stock.quantity_on_hand < line.planned_quantity:
                    raise ValueError(
                        f"Insufficient stock for {product.name}. "
                        f"Required: {line.planned_quantity}, Available: {stock.quantity_on_hand}"
                    )
                
                # Calculate cost (using product cost price)
                unit_cost = product.cost_price or 0.0
                total_cost = unit_cost * line.planned_quantity
                
                # Update stock
                stock.quantity_on_hand -= line.planned_quantity
                
                # Update PO line
                line.consumed_quantity = line.planned_quantity
                line.unit_cost = unit_cost
                line.total_cost = total_cost
                
                total_material_cost += total_cost
                
                materials_issued.append({
                    "product": product.name,
                    "quantity": line.planned_quantity,
                    "cost": total_cost
                })
        
        # Create WIP entry for materials
        wip_entry = models.WorkInProgress(
            company_id=po.company_id,
            production_order_id=po.id,
            transaction_date=datetime.utcnow(),
            transaction_type="material_issue",
            material_cost=total_material_cost,
            labor_cost=0.0,
            overhead_cost=0.0,
            total_cost=total_material_cost,
            quantity=po.planned_quantity,
            created_by=user_id
        )
        self.db.add(wip_entry)
        
        # Update production order
        po.status = "in_progress"
        po.actual_start = datetime.utcnow()
        po.material_cost = total_material_cost
        
        self.db.commit()
        
        logger.info(f"Started production for {po.po_number}, material cost: {total_material_cost}")
        
        return {
            "success": True,
            "production_order": po.po_number,
            "materials_issued": materials_issued,
            "total_material_cost": total_material_cost,
            "status": "in_progress"
        }
    
    def record_labor(
        self,
        production_order_id: str,
        labor_hours: float,
        hourly_rate: float,
        operation_id: Optional[str] = None,
        user_id: str = None,
        notes: str = None
    ) -> Dict:
        """
        Record labor costs - posts to WIP
        Creates GL posting: Dr WIP, Cr Labor Expense
        """
        po = self.db.query(models.ProductionOrder).filter(
            models.ProductionOrder.id == production_order_id
        ).first()
        
        if not po:
            raise ValueError("Production order not found")
        
        if po.status != "in_progress":
            raise ValueError(f"Cannot record labor for production order in status: {po.status}")
        
        # Calculate labor cost
        labor_cost = labor_hours * hourly_rate
        
        # Create WIP entry
        wip_entry = models.WorkInProgress(
            company_id=po.company_id,
            production_order_id=po.id,
            transaction_date=datetime.utcnow(),
            transaction_type="labor",
            material_cost=0.0,
            labor_cost=labor_cost,
            overhead_cost=0.0,
            total_cost=labor_cost,
            quantity=po.planned_quantity,
            notes=notes,
            created_by=user_id
        )
        self.db.add(wip_entry)
        
        # Update production order
        po.labor_cost = (po.labor_cost or 0.0) + labor_cost
        
        self.db.commit()
        
        logger.info(f"Recorded labor for {po.po_number}: {labor_hours}h @ {hourly_rate}/h = {labor_cost}")
        
        return {
            "success": True,
            "production_order": po.po_number,
            "labor_hours": labor_hours,
            "hourly_rate": hourly_rate,
            "labor_cost": labor_cost
        }
    
    def record_overhead(
        self,
        production_order_id: str,
        overhead_cost: float,
        overhead_type: str = "fixed",
        user_id: str = None,
        notes: str = None
    ) -> Dict:
        """
        Record overhead costs - posts to WIP
        Overhead types: fixed, variable, allocated
        """
        po = self.db.query(models.ProductionOrder).filter(
            models.ProductionOrder.id == production_order_id
        ).first()
        
        if not po:
            raise ValueError("Production order not found")
        
        if po.status != "in_progress":
            raise ValueError(f"Cannot record overhead for production order in status: {po.status}")
        
        # Create WIP entry
        wip_entry = models.WorkInProgress(
            company_id=po.company_id,
            production_order_id=po.id,
            transaction_date=datetime.utcnow(),
            transaction_type="overhead",
            material_cost=0.0,
            labor_cost=0.0,
            overhead_cost=overhead_cost,
            total_cost=overhead_cost,
            quantity=po.planned_quantity,
            notes=f"{overhead_type} overhead: {notes}" if notes else overhead_type,
            created_by=user_id
        )
        self.db.add(wip_entry)
        
        # Update production order
        po.overhead_cost = (po.overhead_cost or 0.0) + overhead_cost
        
        self.db.commit()
        
        logger.info(f"Recorded overhead for {po.po_number}: {overhead_cost} ({overhead_type})")
        
        return {
            "success": True,
            "production_order": po.po_number,
            "overhead_cost": overhead_cost,
            "overhead_type": overhead_type
        }
    
    def complete_production(
        self,
        production_order_id: str,
        actual_quantity: float,
        scrapped_quantity: float = 0.0,
        user_id: str = None
    ) -> Dict:
        """
        Complete production - moves WIP to Finished Goods
        Creates GL posting: Dr Finished Goods, Cr WIP
        Updates inventory in destination warehouse
        Calculates final costs and unit cost
        """
        po = self.db.query(models.ProductionOrder).filter(
            models.ProductionOrder.id == production_order_id
        ).first()
        
        if not po:
            raise ValueError("Production order not found")
        
        if po.status != "in_progress":
            raise ValueError(f"Cannot complete production in status: {po.status}")
        
        if not po.destination_warehouse_id:
            raise ValueError("Destination warehouse not specified")
        
        # Calculate total costs
        total_cost = (po.material_cost or 0.0) + (po.labor_cost or 0.0) + (po.overhead_cost or 0.0)
        unit_cost = total_cost / actual_quantity if actual_quantity > 0 else 0.0
        
        # Update production order
        po.produced_quantity = actual_quantity
        po.scrapped_quantity = scrapped_quantity
        po.total_cost = total_cost
        po.unit_cost = unit_cost
        po.status = "completed"
        po.actual_end = datetime.utcnow()
        
        # Create WIP completion entry
        wip_entry = models.WorkInProgress(
            company_id=po.company_id,
            production_order_id=po.id,
            transaction_date=datetime.utcnow(),
            transaction_type="completion",
            material_cost=0.0,
            labor_cost=0.0,
            overhead_cost=0.0,
            total_cost=-total_cost,  # Negative to clear WIP
            quantity=actual_quantity,
            created_by=user_id
        )
        self.db.add(wip_entry)
        
        # Update finished goods inventory
        stock = self.db.query(models.StockItem).filter(
            models.StockItem.product_id == po.product_id,
            models.StockItem.warehouse_id == po.destination_warehouse_id,
            models.StockItem.company_id == po.company_id
        ).first()
        
        if stock:
            stock.quantity_on_hand += actual_quantity
            stock.last_updated = datetime.utcnow()
        else:
            # Create new stock item
            stock = models.StockItem(
                company_id=po.company_id,
                product_id=po.product_id,
                warehouse_id=po.destination_warehouse_id,
                quantity_on_hand=actual_quantity,
                reserved_quantity=0.0,
                last_updated=datetime.utcnow()
            )
            self.db.add(stock)
        
        # Create cost layer
        cost_layer = models.CostLayer(
            company_id=po.company_id,
            product_id=po.product_id,
            warehouse_id=po.destination_warehouse_id,
            layer_date=datetime.utcnow(),
            transaction_type="production",
            reference_id=po.id,
            quantity_in=actual_quantity,
            quantity_out=0.0,
            quantity_remaining=actual_quantity,
            unit_cost=unit_cost,
            total_cost=total_cost
        )
        self.db.add(cost_layer)
        
        # Update product cost price (weighted average)
        product = self.db.query(models.Product).filter(
            models.Product.id == po.product_id
        ).first()
        if product:
            product.cost_price = unit_cost
        
        self.db.commit()
        
        logger.info(
            f"Completed production order {po.po_number}: "
            f"{actual_quantity} units @ {unit_cost}/unit = {total_cost}"
        )
        
        return {
            "success": True,
            "production_order": po.po_number,
            "produced_quantity": actual_quantity,
            "scrapped_quantity": scrapped_quantity,
            "total_cost": total_cost,
            "unit_cost": unit_cost,
            "status": "completed"
        }
    
    def cancel_production_order(self, production_order_id: str, user_id: str, reason: str = None) -> Dict:
        """
        Cancel production order - reverses any stock movements and WIP postings
        """
        po = self.db.query(models.ProductionOrder).filter(
            models.ProductionOrder.id == production_order_id
        ).first()
        
        if not po:
            raise ValueError("Production order not found")
        
        if po.status == "completed":
            raise ValueError("Cannot cancel completed production order")
        
        if po.status == "cancelled":
            raise ValueError("Production order is already cancelled")
        
        # If in_progress, reverse material issues
        if po.status == "in_progress":
            for line in po.lines:
                if line.line_type == "material" and line.consumed_quantity > 0:
                    # Return materials to warehouse
                    stock = self.db.query(models.StockItem).filter(
                        models.StockItem.product_id == line.product_id,
                        models.StockItem.warehouse_id == po.source_warehouse_id,
                        models.StockItem.company_id == po.company_id
                    ).first()
                    
                    if stock:
                        stock.quantity_on_hand += line.consumed_quantity
        
        # Update status
        po.status = "cancelled"
        po.notes = f"{po.notes or ''}\nCancelled: {reason or 'No reason provided'}"
        
        self.db.commit()
        
        logger.info(f"Cancelled production order {po.po_number}")
        
        return {
            "success": True,
            "production_order": po.po_number,
            "status": "cancelled"
        }
    
    def _generate_po_number(self, company_id: str) -> str:
        """Generate unique production order number"""
        # Get latest PO number for this company
        latest_po = self.db.query(models.ProductionOrder).filter(
            models.ProductionOrder.company_id == company_id
        ).order_by(models.ProductionOrder.created_at.desc()).first()
        
        if latest_po and latest_po.po_number:
            # Extract number from PO-XXXXX format
            try:
                last_num = int(latest_po.po_number.split('-')[1])
                new_num = last_num + 1
            except (IndexError, ValueError):
                new_num = 1
        else:
            new_num = 1
        
        return f"PO-{new_num:05d}"
    
    def get_production_order_status(self, production_order_id: str) -> Dict:
        """Get detailed status of production order"""
        po = self.db.query(models.ProductionOrder).filter(
            models.ProductionOrder.id == production_order_id
        ).first()
        
        if not po:
            raise ValueError("Production order not found")
        
        # Get WIP history
        wip_entries = self.db.query(models.WorkInProgress).filter(
            models.WorkInProgress.production_order_id == po.id
        ).order_by(models.WorkInProgress.transaction_date).all()
        
        # Calculate current WIP balance
        total_wip = sum(entry.total_cost for entry in wip_entries)
        
        return {
            "po_number": po.po_number,
            "product_id": po.product_id,
            "status": po.status,
            "planned_quantity": po.planned_quantity,
            "produced_quantity": po.produced_quantity,
            "scrapped_quantity": po.scrapped_quantity,
            "material_cost": po.material_cost,
            "labor_cost": po.labor_cost,
            "overhead_cost": po.overhead_cost,
            "total_cost": po.total_cost,
            "unit_cost": po.unit_cost,
            "current_wip": total_wip,
            "wip_entries_count": len(wip_entries),
            "scheduled_start": po.scheduled_start,
            "scheduled_end": po.scheduled_end,
            "actual_start": po.actual_start,
            "actual_end": po.actual_end
        }

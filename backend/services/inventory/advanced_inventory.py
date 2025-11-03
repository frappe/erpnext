"""
Advanced Inventory Management Service

Features:
- FEFO (First-Expired-First-Out) picking strategy
- Serial number tracking and allocation
- Batch/Lot management
- Quality control holds and releases
- Inventory reservations
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

import models

logger = logging.getLogger(__name__)

class AdvancedInventoryService:
    """Advanced inventory management with FEFO, serial tracking, and quality controls"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # BATCH/LOT MANAGEMENT
    # ========================================================================
    
    def create_batch(
        self,
        company_id: str,
        product_id: str,
        batch_number: str,
        initial_quantity: float,
        production_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
        supplier_id: Optional[str] = None,
        production_order_id: Optional[str] = None,
        notes: str = None
    ) -> models.BatchLot:
        """Create a new batch/lot"""
        # Check for duplicate batch number
        existing = self.db.query(models.BatchLot).filter(
            models.BatchLot.batch_number == batch_number,
            models.BatchLot.company_id == company_id
        ).first()
        
        if existing:
            raise ValueError(f"Batch number {batch_number} already exists")
        
        batch = models.BatchLot(
            company_id=company_id,
            batch_number=batch_number,
            product_id=product_id,
            production_date=production_date,
            expiry_date=expiry_date,
            received_date=date.today(),
            initial_quantity=initial_quantity,
            available_quantity=initial_quantity,
            supplier_id=supplier_id,
            production_order_id=production_order_id,
            quality_status="approved",  # Default approved
            notes=notes
        )
        
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        
        logger.info(f"Created batch {batch_number} for product {product_id}")
        
        return batch
    
    def apply_quality_hold(self, batch_id: str, reason: str, inspector_id: str) -> Dict:
        """Place batch on quality hold"""
        batch = self.db.query(models.BatchLot).filter(
            models.BatchLot.id == batch_id
        ).first()
        
        if not batch:
            raise ValueError("Batch not found")
        
        # Update batch status
        previous_status = batch.quality_status
        batch.quality_status = "hold"
        batch.notes = f"{batch.notes or ''}\nQuality Hold: {reason} (Inspector: {inspector_id})"
        
        self.db.commit()
        
        logger.info(f"Applied quality hold to batch {batch.batch_number}: {reason}")
        
        return {
            "batch_number": batch.batch_number,
            "previous_status": previous_status,
            "current_status": "hold",
            "reason": reason
        }
    
    def release_quality_hold(self, batch_id: str, decision: str, inspector_id: str) -> Dict:
        """Release or reject batch from quality hold"""
        batch = self.db.query(models.BatchLot).filter(
            models.BatchLot.id == batch_id
        ).first()
        
        if not batch:
            raise ValueError("Batch not found")
        
        if batch.quality_status != "hold":
            raise ValueError(f"Batch is not on hold (status: {batch.quality_status})")
        
        if decision not in ["approved", "rejected"]:
            raise ValueError("Decision must be 'approved' or 'rejected'")
        
        batch.quality_status = decision
        batch.notes = f"{batch.notes or ''}\nQuality Decision: {decision} (Inspector: {inspector_id})"
        
        self.db.commit()
        
        logger.info(f"Released batch {batch.batch_number} with decision: {decision}")
        
        return {
            "batch_number": batch.batch_number,
            "decision": decision,
            "available_quantity": batch.available_quantity if decision == "approved" else 0
        }
    
    # ========================================================================
    # FEFO (FIRST-EXPIRED-FIRST-OUT) PICKING
    # ========================================================================
    
    def fefo_pick(
        self,
        company_id: str,
        product_id: str,
        quantity_needed: float,
        warehouse_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Pick inventory using FEFO (First-Expired-First-Out) logic
        Returns list of batches to fulfill the order
        """
        # Get available batches sorted by expiry date (earliest first)
        query = self.db.query(models.BatchLot).filter(
            and_(
                models.BatchLot.company_id == company_id,
                models.BatchLot.product_id == product_id,
                models.BatchLot.available_quantity > 0,
                models.BatchLot.quality_status == "approved"
            )
        )
        
        # Order by expiry date (FEFO), then by production date
        batches = query.order_by(
            models.BatchLot.expiry_date.asc().nullslast(),
            models.BatchLot.production_date.asc()
        ).all()
        
        # Allocate quantity from batches
        allocations = []
        remaining_qty = quantity_needed
        
        for batch in batches:
            if remaining_qty <= 0:
                break
            
            # Check if batch is expired
            if batch.expiry_date and batch.expiry_date < date.today():
                logger.warning(f"Batch {batch.batch_number} is expired, skipping in FEFO pick")
                continue
            
            # Allocate from this batch
            qty_from_batch = min(batch.available_quantity, remaining_qty)
            
            allocations.append({
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "expiry_date": batch.expiry_date,
                "quantity_allocated": qty_from_batch,
                "available_before": batch.available_quantity
            })
            
            remaining_qty -= qty_from_batch
        
        if remaining_qty > 0:
            raise ValueError(
                f"Insufficient inventory. Needed: {quantity_needed}, "
                f"Available: {quantity_needed - remaining_qty}"
            )
        
        return allocations
    
    def consume_inventory_fefo(
        self,
        company_id: str,
        product_id: str,
        quantity: float,
        warehouse_id: Optional[str] = None,
        reference_type: str = None,
        reference_id: str = None
    ) -> Dict:
        """
        Actually consume inventory using FEFO picking
        Updates batch quantities and creates cost layers
        """
        # Get FEFO allocations
        allocations = self.fefo_pick(company_id, product_id, quantity, warehouse_id)
        
        total_cost = 0.0
        batches_consumed = []
        
        for allocation in allocations:
            batch = self.db.query(models.BatchLot).filter(
                models.BatchLot.id == allocation["batch_id"]
            ).first()
            
            if not batch:
                continue
            
            # Reduce batch quantity
            qty_consumed = allocation["quantity_allocated"]
            batch.available_quantity -= qty_consumed
            
            # Get product cost for this batch
            product = self.db.query(models.Product).filter(
                models.Product.id == product_id
            ).first()
            
            unit_cost = product.cost_price or 0.0 if product else 0.0
            batch_cost = qty_consumed * unit_cost
            total_cost += batch_cost
            
            # Create cost layer
            cost_layer = models.CostLayer(
                company_id=company_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                layer_date=datetime.utcnow(),
                transaction_type=reference_type or "sale",
                reference_id=reference_id,
                quantity_in=0.0,
                quantity_out=qty_consumed,
                quantity_remaining=batch.available_quantity,
                unit_cost=unit_cost,
                total_cost=batch_cost,
                batch_lot_id=batch.id
            )
            self.db.add(cost_layer)
            
            batches_consumed.append({
                "batch_number": batch.batch_number,
                "quantity_consumed": qty_consumed,
                "cost": batch_cost
            })
        
        self.db.commit()
        
        logger.info(f"Consumed {quantity} units of product {product_id} using FEFO")
        
        return {
            "product_id": product_id,
            "total_quantity_consumed": quantity,
            "total_cost": total_cost,
            "unit_cost_average": total_cost / quantity if quantity > 0 else 0.0,
            "batches_consumed": batches_consumed
        }
    
    def get_expiring_inventory(
        self,
        company_id: str,
        days_threshold: int = 30
    ) -> List[Dict]:
        """Get inventory that will expire within specified days"""
        threshold_date = date.today() + timedelta(days=days_threshold)
        
        expiring_batches = self.db.query(models.BatchLot).filter(
            and_(
                models.BatchLot.company_id == company_id,
                models.BatchLot.available_quantity > 0,
                models.BatchLot.quality_status == "approved",
                models.BatchLot.expiry_date <= threshold_date,
                models.BatchLot.expiry_date >= date.today()
            )
        ).order_by(models.BatchLot.expiry_date).all()
        
        result = []
        for batch in expiring_batches:
            days_until_expiry = (batch.expiry_date - date.today()).days
            
            product = self.db.query(models.Product).filter(
                models.Product.id == batch.product_id
            ).first()
            
            result.append({
                "batch_number": batch.batch_number,
                "product_id": batch.product_id,
                "product_name": product.name if product else None,
                "expiry_date": batch.expiry_date,
                "days_until_expiry": days_until_expiry,
                "available_quantity": batch.available_quantity,
                "urgency": "critical" if days_until_expiry <= 7 else "warning"
            })
        
        return result
    
    # ========================================================================
    # SERIAL NUMBER TRACKING
    # ========================================================================
    
    def assign_serial_numbers(
        self,
        company_id: str,
        product_id: str,
        serial_numbers: List[str],
        batch_lot_id: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        manufactured_date: Optional[date] = None,
        warranty_months: int = 12
    ) -> List[models.SerialNumber]:
        """Assign serial numbers to products"""
        created_serials = []
        
        for serial in serial_numbers:
            # Check for duplicates
            existing = self.db.query(models.SerialNumber).filter(
                models.SerialNumber.serial_number == serial,
                models.SerialNumber.company_id == company_id
            ).first()
            
            if existing:
                logger.warning(f"Serial number {serial} already exists, skipping")
                continue
            
            # Calculate warranty expiry
            warranty_expiry = None
            if manufactured_date and warranty_months > 0:
                warranty_expiry = manufactured_date + timedelta(days=warranty_months * 30)
            
            serial_obj = models.SerialNumber(
                company_id=company_id,
                serial_number=serial,
                product_id=product_id,
                batch_lot_id=batch_lot_id,
                warehouse_id=warehouse_id,
                status="in_stock",
                manufactured_date=manufactured_date,
                warranty_expiry=warranty_expiry
            )
            
            self.db.add(serial_obj)
            created_serials.append(serial_obj)
        
        self.db.commit()
        
        logger.info(f"Assigned {len(created_serials)} serial numbers for product {product_id}")
        
        return created_serials
    
    def transfer_serial_number(
        self,
        serial_number: str,
        to_warehouse_id: Optional[str] = None,
        to_customer_id: Optional[str] = None,
        status: str = None
    ) -> models.SerialNumber:
        """Transfer serial number to different location or mark as sold"""
        serial = self.db.query(models.SerialNumber).filter(
            models.SerialNumber.serial_number == serial_number
        ).first()
        
        if not serial:
            raise ValueError(f"Serial number {serial_number} not found")
        
        if to_warehouse_id:
            serial.warehouse_id = to_warehouse_id
            serial.current_location = f"Warehouse {to_warehouse_id}"
        
        if to_customer_id:
            serial.customer_id = to_customer_id
            serial.status = "sold"
        
        if status:
            serial.status = status
        
        self.db.commit()
        
        logger.info(f"Transferred serial number {serial_number}")
        
        return serial
    
    def get_serial_number_history(self, serial_number: str) -> Dict:
        """Get complete history and current status of a serial number"""
        serial = self.db.query(models.SerialNumber).filter(
            models.SerialNumber.serial_number == serial_number
        ).first()
        
        if not serial:
            raise ValueError(f"Serial number {serial_number} not found")
        
        # Get product info
        product = self.db.query(models.Product).filter(
            models.Product.id == serial.product_id
        ).first()
        
        # Get batch info
        batch = None
        if serial.batch_lot_id:
            batch = self.db.query(models.BatchLot).filter(
                models.BatchLot.id == serial.batch_lot_id
            ).first()
        
        # Get warehouse info
        warehouse = None
        if serial.warehouse_id:
            warehouse = self.db.query(models.Warehouse).filter(
                models.Warehouse.id == serial.warehouse_id
            ).first()
        
        # Get customer info
        customer = None
        if serial.customer_id:
            customer = self.db.query(models.Customer).filter(
                models.Customer.id == serial.customer_id
            ).first()
        
        # Calculate warranty status
        warranty_status = "unknown"
        if serial.warranty_expiry:
            if serial.warranty_expiry >= date.today():
                warranty_status = "active"
            else:
                warranty_status = "expired"
        
        return {
            "serial_number": serial.serial_number,
            "status": serial.status,
            "product": {
                "id": product.id,
                "name": product.name,
                "code": product.code
            } if product else None,
            "batch": {
                "batch_number": batch.batch_number,
                "production_date": batch.production_date,
                "expiry_date": batch.expiry_date
            } if batch else None,
            "warehouse": {
                "id": warehouse.id,
                "name": warehouse.name,
                "code": warehouse.code
            } if warehouse else None,
            "customer": {
                "id": customer.id,
                "name": customer.name
            } if customer else None,
            "manufactured_date": serial.manufactured_date,
            "warranty_expiry": serial.warranty_expiry,
            "warranty_status": warranty_status,
            "current_location": serial.current_location,
            "created_at": serial.created_at
        }
    
    # ========================================================================
    # QUALITY CONTROL
    # ========================================================================
    
    def create_quality_inspection(
        self,
        company_id: str,
        inspection_type: str,
        inspection_date: date,
        product_id: Optional[str] = None,
        batch_lot_id: Optional[str] = None,
        production_order_id: Optional[str] = None,
        quantity_inspected: float = 0.0,
        quantity_passed: float = 0.0,
        quantity_failed: float = 0.0,
        decision: str = "approved",
        inspector_id: Optional[str] = None,
        notes: str = None
    ) -> models.QualityControl:
        """Create a quality control inspection record"""
        # Generate QC number
        qc_number = self._generate_qc_number(company_id)
        
        qc = models.QualityControl(
            company_id=company_id,
            qc_number=qc_number,
            inspection_date=inspection_date,
            inspection_type=inspection_type,
            product_id=product_id,
            batch_lot_id=batch_lot_id,
            production_order_id=production_order_id,
            quantity_inspected=quantity_inspected,
            quantity_passed=quantity_passed,
            quantity_failed=quantity_failed,
            decision=decision,
            inspector_id=inspector_id,
            notes=notes
        )
        
        self.db.add(qc)
        self.db.commit()
        self.db.refresh(qc)
        
        # If batch provided and inspection failed, apply hold
        if batch_lot_id and decision in ["rejected", "hold"]:
            self.apply_quality_hold(batch_lot_id, f"QC Inspection {qc_number}: {decision}", inspector_id or "system")
        
        logger.info(f"Created QC inspection {qc_number}: {decision}")
        
        return qc
    
    def _generate_qc_number(self, company_id: str) -> str:
        """Generate unique QC inspection number"""
        latest_qc = self.db.query(models.QualityControl).filter(
            models.QualityControl.company_id == company_id
        ).order_by(models.QualityControl.created_at.desc()).first()
        
        if latest_qc and latest_qc.qc_number:
            try:
                last_num = int(latest_qc.qc_number.split('-')[1])
                new_num = last_num + 1
            except (IndexError, ValueError):
                new_num = 1
        else:
            new_num = 1
        
        return f"QC-{new_num:05d}"

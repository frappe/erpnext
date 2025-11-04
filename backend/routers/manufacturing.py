"""
Manufacturing Management API Router

Handles production orders, bill of materials (BOM), and manufacturing workflows
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

import models
import schemas
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/manufacturing", tags=["manufacturing"])


# ============================================================================
# BILL OF MATERIALS (BOM)
# ============================================================================

@router.post("/bom", response_model=dict)
def create_bom(
    bom: schemas.BOMCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a Bill of Materials"""
    
    # Verify product exists
    product = db.query(models.Product).filter(
        and_(
            models.Product.id == bom.product_id,
            models.Product.company_id == current_user.company_id
        )
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Generate BOM number
    bom_count = db.query(func.count(models.BillOfMaterials.id)).filter(
        models.BillOfMaterials.company_id == current_user.company_id
    ).scalar()
    bom_number = f"BOM-{date.today().strftime('%Y%m')}-{bom_count + 1:05d}"
    
    # Create BOM
    db_bom = models.BillOfMaterials(
        company_id=current_user.company_id,
        bom_number=bom_number,
        product_id=bom.product_id,
        product_quantity=bom.product_quantity or Decimal(1),
        description=bom.description,
        is_active=True,
        created_by=current_user.id
    )
    
    db.add(db_bom)
    db.flush()
    
    # Create BOM lines
    for line_data in bom.lines:
        db_line = models.BOMLine(
            bom_id=db_bom.id,
            component_id=line_data.component_id,
            quantity=line_data.quantity,
            unit_cost=line_data.unit_cost,
            scrap_percentage=line_data.scrap_percentage or 0
        )
        db.add(db_line)
    
    db.commit()
    db.refresh(db_bom)
    
    return {
        "id": db_bom.id,
        "bom_number": db_bom.bom_number,
        "product_id": db_bom.product_id,
        "message": "Bill of Materials created successfully"
    }


@router.get("/bom", response_model=List[dict])
def list_boms(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List Bills of Materials"""
    
    query = db.query(models.BillOfMaterials).filter(
        models.BillOfMaterials.company_id == current_user.company_id
    )
    
    if product_id:
        query = query.filter(models.BillOfMaterials.product_id == product_id)
    
    if is_active is not None:
        query = query.filter(models.BillOfMaterials.is_active == is_active)
    
    boms = query.offset(skip).limit(limit).all()
    
    result = []
    for bom in boms:
        product = db.query(models.Product).filter(models.Product.id == bom.product_id).first()
        result.append({
            "id": bom.id,
            "bom_number": bom.bom_number,
            "product_id": bom.product_id,
            "product_name": product.product_name if product else None,
            "product_quantity": float(bom.product_quantity),
            "is_active": bom.is_active
        })
    
    return result


@router.get("/bom/{bom_id}", response_model=dict)
def get_bom(
    bom_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get BOM details with components"""
    
    bom = db.query(models.BillOfMaterials).filter(
        and_(
            models.BillOfMaterials.id == bom_id,
            models.BillOfMaterials.company_id == current_user.company_id
        )
    ).first()
    
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    
    # Get product
    product = db.query(models.Product).filter(models.Product.id == bom.product_id).first()
    
    # Get BOM lines
    lines = db.query(models.BOMLine).filter(models.BOMLine.bom_id == bom_id).all()
    
    components = []
    total_cost = Decimal(0)
    
    for line in lines:
        component = db.query(models.Product).filter(models.Product.id == line.component_id).first()
        line_cost = line.quantity * (line.unit_cost or Decimal(0))
        total_cost += line_cost
        
        components.append({
            "id": line.id,
            "component_id": line.component_id,
            "component_name": component.product_name if component else None,
            "quantity": float(line.quantity),
            "unit_cost": float(line.unit_cost) if line.unit_cost else 0,
            "line_cost": float(line_cost),
            "scrap_percentage": float(line.scrap_percentage) if line.scrap_percentage else 0
        })
    
    return {
        "id": bom.id,
        "bom_number": bom.bom_number,
        "product": {
            "id": product.id if product else None,
            "name": product.product_name if product else None,
            "code": product.product_code if product else None
        },
        "product_quantity": float(bom.product_quantity),
        "description": bom.description,
        "is_active": bom.is_active,
        "components": components,
        "total_cost": float(total_cost),
        "unit_cost": float(total_cost / bom.product_quantity) if bom.product_quantity else 0
    }


# ============================================================================
# PRODUCTION ORDERS
# ============================================================================

@router.post("/production-orders", response_model=dict)
def create_production_order(
    order: schemas.ProductionOrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new production order"""
    
    # Verify product exists
    product = db.query(models.Product).filter(
        and_(
            models.Product.id == order.product_id,
            models.Product.company_id == current_user.company_id
        )
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get BOM if provided
    bom = None
    if order.bom_id:
        bom = db.query(models.BillOfMaterials).filter(
            and_(
                models.BillOfMaterials.id == order.bom_id,
                models.BillOfMaterials.company_id == current_user.company_id
            )
        ).first()
        
        if not bom:
            raise HTTPException(status_code=404, detail="BOM not found")
    
    # Generate production order number
    po_count = db.query(func.count(models.ProductionOrder.id)).filter(
        models.ProductionOrder.company_id == current_user.company_id
    ).scalar()
    production_number = f"PRO-{date.today().strftime('%Y%m')}-{po_count + 1:05d}"
    
    # Create production order
    db_order = models.ProductionOrder(
        company_id=current_user.company_id,
        production_number=production_number,
        product_id=order.product_id,
        bom_id=order.bom_id,
        quantity_planned=order.quantity_planned,
        quantity_produced=Decimal(0),
        start_date=order.start_date or date.today(),
        planned_end_date=order.planned_end_date,
        warehouse_id=order.warehouse_id,
        status="draft",
        notes=order.notes,
        created_by=current_user.id
    )
    
    db.add(db_order)
    db.flush()
    
    # If BOM exists, create production order lines from BOM components
    if bom:
        bom_lines = db.query(models.BOMLine).filter(models.BOMLine.bom_id == bom.id).all()
        
        for bom_line in bom_lines:
            # Calculate required quantity based on production quantity
            required_qty = bom_line.quantity * order.quantity_planned
            
            db_po_line = models.ProductionOrderLine(
                production_order_id=db_order.id,
                component_id=bom_line.component_id,
                quantity_required=required_qty,
                quantity_consumed=Decimal(0),
                unit_cost=bom_line.unit_cost
            )
            db.add(db_po_line)
    
    db.commit()
    db.refresh(db_order)
    
    return {
        "id": db_order.id,
        "production_number": db_order.production_number,
        "product_id": db_order.product_id,
        "quantity_planned": float(db_order.quantity_planned),
        "status": db_order.status,
        "message": "Production order created successfully"
    }


@router.get("/production-orders", response_model=List[dict])
def list_production_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    product_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List production orders"""
    
    query = db.query(models.ProductionOrder).filter(
        models.ProductionOrder.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.ProductionOrder.status == status)
    
    if product_id:
        query = query.filter(models.ProductionOrder.product_id == product_id)
    
    orders = query.order_by(models.ProductionOrder.start_date.desc()).offset(skip).limit(limit).all()
    
    result = []
    for order in orders:
        product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
        result.append({
            "id": order.id,
            "production_number": order.production_number,
            "product_name": product.product_name if product else None,
            "quantity_planned": float(order.quantity_planned),
            "quantity_produced": float(order.quantity_produced),
            "start_date": order.start_date.isoformat() if order.start_date else None,
            "planned_end_date": order.planned_end_date.isoformat() if order.planned_end_date else None,
            "status": order.status
        })
    
    return result


@router.get("/production-orders/{order_id}", response_model=dict)
def get_production_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get production order details"""
    
    order = db.query(models.ProductionOrder).filter(
        and_(
            models.ProductionOrder.id == order_id,
            models.ProductionOrder.company_id == current_user.company_id
        )
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")
    
    # Get product
    product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
    
    # Get production order lines
    lines = db.query(models.ProductionOrderLine).filter(
        models.ProductionOrderLine.production_order_id == order_id
    ).all()
    
    components = []
    for line in lines:
        component = db.query(models.Product).filter(models.Product.id == line.component_id).first()
        components.append({
            "id": line.id,
            "component_id": line.component_id,
            "component_name": component.product_name if component else None,
            "quantity_required": float(line.quantity_required),
            "quantity_consumed": float(line.quantity_consumed),
            "unit_cost": float(line.unit_cost) if line.unit_cost else 0
        })
    
    return {
        "id": order.id,
        "production_number": order.production_number,
        "product": {
            "id": product.id if product else None,
            "name": product.product_name if product else None
        },
        "quantity_planned": float(order.quantity_planned),
        "quantity_produced": float(order.quantity_produced),
        "start_date": order.start_date.isoformat() if order.start_date else None,
        "planned_end_date": order.planned_end_date.isoformat() if order.planned_end_date else None,
        "actual_end_date": order.actual_end_date.isoformat() if order.actual_end_date else None,
        "status": order.status,
        "notes": order.notes,
        "components": components
    }


@router.post("/production-orders/{order_id}/start", response_model=dict)
def start_production_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Start a production order"""
    
    order = db.query(models.ProductionOrder).filter(
        and_(
            models.ProductionOrder.id == order_id,
            models.ProductionOrder.company_id == current_user.company_id
        )
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")
    
    if order.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft orders can be started")
    
    order.status = "in_progress"
    order.start_date = date.today()
    
    db.commit()
    
    return {"message": "Production order started", "status": order.status}


@router.post("/production-orders/{order_id}/complete", response_model=dict)
def complete_production_order(
    order_id: str,
    actual_quantity: float,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Complete a production order and update stock"""
    
    order = db.query(models.ProductionOrder).filter(
        and_(
            models.ProductionOrder.id == order_id,
            models.ProductionOrder.company_id == current_user.company_id
        )
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Production order not found")
    
    if order.status != "in_progress":
        raise HTTPException(status_code=400, detail="Only in-progress orders can be completed")
    
    # Update production order
    order.status = "completed"
    order.quantity_produced = Decimal(str(actual_quantity))
    order.actual_end_date = date.today()
    
    # Create stock movement for finished product
    if order.warehouse_id:
        stock_movement = models.StockMovement(
            company_id=current_user.company_id,
            product_id=order.product_id,
            warehouse_id=order.warehouse_id,
            movement_type="production",
            quantity=Decimal(str(actual_quantity)),
            reference_type="production_order",
            reference_id=order.id,
            movement_date=date.today(),
            created_by=current_user.id
        )
        db.add(stock_movement)
        
        # Update stock item
        stock_item = db.query(models.StockItem).filter(
            and_(
                models.StockItem.product_id == order.product_id,
                models.StockItem.warehouse_id == order.warehouse_id,
                models.StockItem.company_id == current_user.company_id
            )
        ).first()
        
        if not stock_item:
            stock_item = models.StockItem(
                company_id=current_user.company_id,
                product_id=order.product_id,
                warehouse_id=order.warehouse_id,
                quantity_on_hand=Decimal(0),
                quantity_reserved=Decimal(0)
            )
            db.add(stock_item)
            db.flush()
        
        stock_item.quantity_on_hand += Decimal(str(actual_quantity))
    
    db.commit()
    
    return {
        "message": "Production order completed",
        "status": order.status,
        "quantity_produced": float(order.quantity_produced)
    }

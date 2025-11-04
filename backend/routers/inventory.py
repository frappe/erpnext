"""
Inventory Management API Router

Handles products, warehouses, stock movements, and inventory tracking
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

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


# ============================================================================
# PRODUCT MANAGEMENT
# ============================================================================

@router.post("/products", response_model=dict)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new product"""
    
    # Check for duplicate product code
    existing = db.query(models.Product).filter(
        and_(
            models.Product.company_id == current_user.company_id,
            models.Product.product_code == product.product_code
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Product code already exists")
    
    # Create product
    db_product = models.Product(
        company_id=current_user.company_id,
        **product.dict()
    )
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    return {
        "id": db_product.id,
        "product_code": db_product.product_code,
        "product_name": db_product.product_name,
        "message": "Product created successfully"
    }


@router.get("/products", response_model=List[dict])
def list_products(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    product_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all products"""
    
    query = db.query(models.Product).filter(
        models.Product.company_id == current_user.company_id
    )
    
    if search:
        query = query.filter(
            or_(
                models.Product.product_name.ilike(f"%{search}%"),
                models.Product.product_code.ilike(f"%{search}%"),
                models.Product.barcode.ilike(f"%{search}%")
            )
        )
    
    if product_type:
        query = query.filter(models.Product.product_type == product_type)
    
    products = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": p.id,
            "product_code": p.product_code,
            "product_name": p.product_name,
            "product_type": p.product_type,
            "unit_of_measure": p.unit_of_measure,
            "cost_price": float(p.cost_price) if p.cost_price else 0,
            "selling_price": float(p.selling_price) if p.selling_price else 0,
            "is_active": p.is_active
        }
        for p in products
    ]


@router.get("/products/{product_id}", response_model=dict)
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get product details"""
    
    product = db.query(models.Product).filter(
        and_(
            models.Product.id == product_id,
            models.Product.company_id == current_user.company_id
        )
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get stock levels across all warehouses
    stock_items = db.query(models.StockItem).filter(
        models.StockItem.product_id == product_id
    ).all()
    
    total_stock = sum(s.quantity_on_hand for s in stock_items if s.quantity_on_hand)
    
    return {
        "id": product.id,
        "product_code": product.product_code,
        "product_name": product.product_name,
        "description": product.description,
        "product_type": product.product_type,
        "unit_of_measure": product.unit_of_measure,
        "cost_price": float(product.cost_price) if product.cost_price else 0,
        "selling_price": float(product.selling_price) if product.selling_price else 0,
        "barcode": product.barcode,
        "is_active": product.is_active,
        "track_inventory": product.track_inventory,
        "track_batches": product.track_batches,
        "track_serials": product.track_serials,
        "total_stock": float(total_stock) if total_stock else 0,
        "created_at": product.created_at.isoformat() if product.created_at else None
    }


@router.put("/products/{product_id}", response_model=dict)
def update_product(
    product_id: str,
    product_update: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update product"""
    
    db_product = db.query(models.Product).filter(
        and_(
            models.Product.id == product_id,
            models.Product.company_id == current_user.company_id
        )
    ).first()
    
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for key, value in product_update.dict(exclude_unset=True).items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    
    return {"message": "Product updated successfully"}


# ============================================================================
# WAREHOUSE MANAGEMENT
# ============================================================================

@router.post("/warehouses", response_model=dict)
def create_warehouse(
    warehouse: schemas.WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new warehouse"""
    
    db_warehouse = models.Warehouse(
        company_id=current_user.company_id,
        **warehouse.dict()
    )
    
    db.add(db_warehouse)
    db.commit()
    db.refresh(db_warehouse)
    
    return {
        "id": db_warehouse.id,
        "warehouse_code": db_warehouse.warehouse_code,
        "warehouse_name": db_warehouse.warehouse_name,
        "message": "Warehouse created successfully"
    }


@router.get("/warehouses", response_model=List[dict])
def list_warehouses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all warehouses"""
    
    warehouses = db.query(models.Warehouse).filter(
        models.Warehouse.company_id == current_user.company_id
    ).all()
    
    return [
        {
            "id": w.id,
            "warehouse_code": w.warehouse_code,
            "warehouse_name": w.warehouse_name,
            "location": w.location,
            "is_active": w.is_active
        }
        for w in warehouses
    ]


# ============================================================================
# STOCK MANAGEMENT
# ============================================================================

@router.get("/stock", response_model=List[dict])
def list_stock(
    warehouse_id: Optional[str] = None,
    product_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List stock items across warehouses"""
    
    query = db.query(models.StockItem).filter(
        models.StockItem.company_id == current_user.company_id
    )
    
    if warehouse_id:
        query = query.filter(models.StockItem.warehouse_id == warehouse_id)
    
    if product_id:
        query = query.filter(models.StockItem.product_id == product_id)
    
    stock_items = query.all()
    
    result = []
    for stock in stock_items:
        # Get product info
        product = db.query(models.Product).filter(
            models.Product.id == stock.product_id
        ).first()
        
        # Get warehouse info
        warehouse = db.query(models.Warehouse).filter(
            models.Warehouse.id == stock.warehouse_id
        ).first()
        
        result.append({
            "id": stock.id,
            "product_id": stock.product_id,
            "product_code": product.product_code if product else None,
            "product_name": product.product_name if product else None,
            "warehouse_id": stock.warehouse_id,
            "warehouse_name": warehouse.warehouse_name if warehouse else None,
            "quantity_on_hand": float(stock.quantity_on_hand) if stock.quantity_on_hand else 0,
            "quantity_reserved": float(stock.quantity_reserved) if stock.quantity_reserved else 0,
            "quantity_available": float(stock.quantity_on_hand - stock.quantity_reserved) if stock.quantity_on_hand and stock.quantity_reserved else 0,
            "reorder_level": float(stock.reorder_level) if stock.reorder_level else 0,
            "reorder_quantity": float(stock.reorder_quantity) if stock.reorder_quantity else 0
        })
    
    return result


@router.post("/stock/movements", response_model=dict)
def create_stock_movement(
    movement: schemas.StockMovementCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Record a stock movement"""
    
    # Verify product exists
    product = db.query(models.Product).filter(
        and_(
            models.Product.id == movement.product_id,
            models.Product.company_id == current_user.company_id
        )
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Create movement record
    db_movement = models.StockMovement(
        company_id=current_user.company_id,
        product_id=movement.product_id,
        warehouse_id=movement.warehouse_id,
        movement_type=movement.movement_type,
        quantity=movement.quantity,
        unit_cost=movement.unit_cost,
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        notes=movement.notes,
        movement_date=movement.movement_date or date.today(),
        created_by=current_user.id
    )
    
    db.add(db_movement)
    
    # Update stock levels
    stock_item = db.query(models.StockItem).filter(
        and_(
            models.StockItem.product_id == movement.product_id,
            models.StockItem.warehouse_id == movement.warehouse_id,
            models.StockItem.company_id == current_user.company_id
        )
    ).first()
    
    if not stock_item:
        # Create new stock item
        stock_item = models.StockItem(
            company_id=current_user.company_id,
            product_id=movement.product_id,
            warehouse_id=movement.warehouse_id,
            quantity_on_hand=Decimal(0),
            quantity_reserved=Decimal(0)
        )
        db.add(stock_item)
        db.flush()
    
    # Adjust quantity based on movement type
    if movement.movement_type in ["purchase", "production", "adjustment_in", "transfer_in"]:
        stock_item.quantity_on_hand += movement.quantity
    elif movement.movement_type in ["sale", "production_consumption", "adjustment_out", "transfer_out"]:
        if stock_item.quantity_on_hand < movement.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        stock_item.quantity_on_hand -= movement.quantity
    
    db.commit()
    db.refresh(db_movement)
    
    return {
        "id": db_movement.id,
        "movement_type": db_movement.movement_type,
        "quantity": float(db_movement.quantity),
        "new_stock_level": float(stock_item.quantity_on_hand),
        "message": "Stock movement recorded successfully"
    }


@router.get("/stock/movements", response_model=List[dict])
def list_stock_movements(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    movement_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List stock movements"""
    
    query = db.query(models.StockMovement).filter(
        models.StockMovement.company_id == current_user.company_id
    )
    
    if product_id:
        query = query.filter(models.StockMovement.product_id == product_id)
    
    if warehouse_id:
        query = query.filter(models.StockMovement.warehouse_id == warehouse_id)
    
    if movement_type:
        query = query.filter(models.StockMovement.movement_type == movement_type)
    
    movements = query.order_by(models.StockMovement.movement_date.desc()).offset(skip).limit(limit).all()
    
    result = []
    for movement in movements:
        product = db.query(models.Product).filter(models.Product.id == movement.product_id).first()
        warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == movement.warehouse_id).first()
        
        result.append({
            "id": movement.id,
            "movement_date": movement.movement_date.isoformat() if movement.movement_date else None,
            "movement_type": movement.movement_type,
            "product_code": product.product_code if product else None,
            "product_name": product.product_name if product else None,
            "warehouse_name": warehouse.warehouse_name if warehouse else None,
            "quantity": float(movement.quantity),
            "unit_cost": float(movement.unit_cost) if movement.unit_cost else 0,
            "reference_type": movement.reference_type,
            "notes": movement.notes
        })
    
    return result


# ============================================================================
# STOCK REPORTS
# ============================================================================

@router.get("/reports/stock-valuation", response_model=List[dict])
def get_stock_valuation(
    warehouse_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get stock valuation report"""
    
    query = db.query(models.StockItem).filter(
        models.StockItem.company_id == current_user.company_id
    )
    
    if warehouse_id:
        query = query.filter(models.StockItem.warehouse_id == warehouse_id)
    
    stock_items = query.all()
    
    valuation = []
    total_value = Decimal(0)
    
    for stock in stock_items:
        product = db.query(models.Product).filter(models.Product.id == stock.product_id).first()
        warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == stock.warehouse_id).first()
        
        if not product:
            continue
        
        qty = stock.quantity_on_hand or Decimal(0)
        cost = product.cost_price or Decimal(0)
        value = qty * cost
        total_value += value
        
        valuation.append({
            "product_code": product.product_code,
            "product_name": product.product_name,
            "warehouse": warehouse.warehouse_name if warehouse else "Unknown",
            "quantity": float(qty),
            "unit_cost": float(cost),
            "total_value": float(value)
        })
    
    return valuation

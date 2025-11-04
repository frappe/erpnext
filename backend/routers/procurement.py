"""
Procurement Management API Router

Handles suppliers, purchase orders, goods received notes, and accounts payable
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

router = APIRouter(prefix="/api/procurement", tags=["procurement"])


# ============================================================================
# SUPPLIER MANAGEMENT
# ============================================================================

@router.post("/suppliers", response_model=dict)
def create_supplier(
    supplier: schemas.SupplierCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new supplier"""
    
    # Check for duplicate supplier code
    existing = db.query(models.Supplier).filter(
        and_(
            models.Supplier.company_id == current_user.company_id,
            models.Supplier.supplier_code == supplier.supplier_code
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Supplier code already exists")
    
    # Create supplier
    db_supplier = models.Supplier(
        company_id=current_user.company_id,
        **supplier.dict()
    )
    
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    
    return {
        "id": db_supplier.id,
        "supplier_code": db_supplier.supplier_code,
        "supplier_name": db_supplier.supplier_name,
        "message": "Supplier created successfully"
    }


@router.get("/suppliers", response_model=List[dict])
def list_suppliers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all suppliers"""
    
    query = db.query(models.Supplier).filter(
        models.Supplier.company_id == current_user.company_id
    )
    
    if search:
        query = query.filter(
            or_(
                models.Supplier.supplier_name.ilike(f"%{search}%"),
                models.Supplier.supplier_code.ilike(f"%{search}%"),
                models.Supplier.email.ilike(f"%{search}%")
            )
        )
    
    suppliers = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": s.id,
            "supplier_code": s.supplier_code,
            "supplier_name": s.supplier_name,
            "email": s.email,
            "phone": s.phone,
            "tax_id": s.tax_id,
            "payment_terms_days": s.payment_terms_days,
            "is_active": s.is_active
        }
        for s in suppliers
    ]


@router.get("/suppliers/{supplier_id}", response_model=dict)
def get_supplier(
    supplier_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get supplier details"""
    
    supplier = db.query(models.Supplier).filter(
        and_(
            models.Supplier.id == supplier_id,
            models.Supplier.company_id == current_user.company_id
        )
    ).first()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    return {
        "id": supplier.id,
        "supplier_code": supplier.supplier_code,
        "supplier_name": supplier.supplier_name,
        "email": supplier.email,
        "phone": supplier.phone,
        "address": supplier.address,
        "city": supplier.city,
        "country": supplier.country,
        "tax_id": supplier.tax_id,
        "payment_terms_days": supplier.payment_terms_days,
        "is_active": supplier.is_active,
        "created_at": supplier.created_at.isoformat() if supplier.created_at else None
    }


@router.put("/suppliers/{supplier_id}", response_model=dict)
def update_supplier(
    supplier_id: str,
    supplier_update: schemas.SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update supplier"""
    
    db_supplier = db.query(models.Supplier).filter(
        and_(
            models.Supplier.id == supplier_id,
            models.Supplier.company_id == current_user.company_id
        )
    ).first()
    
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    for key, value in supplier_update.dict(exclude_unset=True).items():
        setattr(db_supplier, key, value)
    
    db.commit()
    db.refresh(db_supplier)
    
    return {"message": "Supplier updated successfully"}


# ============================================================================
# PURCHASE ORDERS
# ============================================================================

@router.post("/purchase-orders", response_model=dict)
def create_purchase_order(
    order: schemas.PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new purchase order"""
    
    # Verify supplier exists
    supplier = db.query(models.Supplier).filter(
        and_(
            models.Supplier.id == order.supplier_id,
            models.Supplier.company_id == current_user.company_id
        )
    ).first()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Generate PO number
    po_count = db.query(func.count(models.PurchaseOrder.id)).filter(
        models.PurchaseOrder.company_id == current_user.company_id
    ).scalar()
    po_number = f"PO-{date.today().strftime('%Y%m')}-{po_count + 1:05d}"
    
    # Calculate totals
    subtotal = sum(line.quantity * line.unit_price for line in order.lines)
    tax_amount = subtotal * Decimal(0.16)  # 16% VAT default
    total_amount = subtotal + tax_amount
    
    # Create purchase order
    db_order = models.PurchaseOrder(
        company_id=current_user.company_id,
        po_number=po_number,
        supplier_id=order.supplier_id,
        order_date=order.order_date or date.today(),
        expected_delivery_date=order.expected_delivery_date,
        currency=order.currency or "ZMW",
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        notes=order.notes,
        status="draft",
        created_by=current_user.id
    )
    
    db.add(db_order)
    db.flush()
    
    # Create order lines
    for line_data in order.lines:
        db_line = models.PurchaseOrderLine(
            purchase_order_id=db_order.id,
            product_id=line_data.product_id,
            description=line_data.description,
            quantity=line_data.quantity,
            unit_price=line_data.unit_price,
            tax_rate=line_data.tax_rate or 0.16,
            line_total=line_data.quantity * line_data.unit_price
        )
        db.add(db_line)
    
    db.commit()
    db.refresh(db_order)
    
    return {
        "id": db_order.id,
        "po_number": db_order.po_number,
        "total_amount": float(db_order.total_amount),
        "status": db_order.status,
        "message": "Purchase order created successfully"
    }


@router.get("/purchase-orders", response_model=List[dict])
def list_purchase_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    supplier_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List purchase orders"""
    
    query = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.PurchaseOrder.status == status)
    
    if supplier_id:
        query = query.filter(models.PurchaseOrder.supplier_id == supplier_id)
    
    orders = query.order_by(models.PurchaseOrder.order_date.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": o.id,
            "po_number": o.po_number,
            "supplier_id": o.supplier_id,
            "order_date": o.order_date.isoformat() if o.order_date else None,
            "expected_delivery_date": o.expected_delivery_date.isoformat() if o.expected_delivery_date else None,
            "total_amount": float(o.total_amount),
            "currency": o.currency,
            "status": o.status
        }
        for o in orders
    ]


@router.get("/purchase-orders/{po_id}", response_model=dict)
def get_purchase_order(
    po_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get purchase order details with line items"""
    
    order = db.query(models.PurchaseOrder).filter(
        and_(
            models.PurchaseOrder.id == po_id,
            models.PurchaseOrder.company_id == current_user.company_id
        )
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    # Get supplier
    supplier = db.query(models.Supplier).filter(models.Supplier.id == order.supplier_id).first()
    
    # Get order lines
    lines = db.query(models.PurchaseOrderLine).filter(
        models.PurchaseOrderLine.purchase_order_id == po_id
    ).all()
    
    return {
        "id": order.id,
        "po_number": order.po_number,
        "supplier": {
            "id": supplier.id if supplier else None,
            "name": supplier.supplier_name if supplier else None,
            "code": supplier.supplier_code if supplier else None
        },
        "order_date": order.order_date.isoformat() if order.order_date else None,
        "expected_delivery_date": order.expected_delivery_date.isoformat() if order.expected_delivery_date else None,
        "currency": order.currency,
        "subtotal": float(order.subtotal),
        "tax_amount": float(order.tax_amount),
        "total_amount": float(order.total_amount),
        "status": order.status,
        "notes": order.notes,
        "lines": [
            {
                "id": line.id,
                "product_id": line.product_id,
                "description": line.description,
                "quantity": float(line.quantity),
                "unit_price": float(line.unit_price),
                "tax_rate": float(line.tax_rate) if line.tax_rate else 0,
                "line_total": float(line.line_total)
            }
            for line in lines
        ]
    }


@router.post("/purchase-orders/{po_id}/approve", response_model=dict)
def approve_purchase_order(
    po_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Approve a purchase order"""
    
    order = db.query(models.PurchaseOrder).filter(
        and_(
            models.PurchaseOrder.id == po_id,
            models.PurchaseOrder.company_id == current_user.company_id
        )
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if order.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft orders can be approved")
    
    order.status = "approved"
    order.approved_date = datetime.utcnow()
    order.approved_by = current_user.id
    
    db.commit()
    
    return {"message": "Purchase order approved successfully", "status": order.status}


# ============================================================================
# ACCOUNTS PAYABLE
# ============================================================================

@router.get("/payables/aging", response_model=List[dict])
def get_ap_aging(
    supplier_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get accounts payable aging report"""
    
    query = db.query(models.PurchaseOrder).filter(
        and_(
            models.PurchaseOrder.company_id == current_user.company_id,
            models.PurchaseOrder.status.in_(["approved", "received"]),
            models.PurchaseOrder.total_amount > 0
        )
    )
    
    if supplier_id:
        query = query.filter(models.PurchaseOrder.supplier_id == supplier_id)
    
    orders = query.all()
    
    aging_data = []
    today = date.today()
    
    for order in orders:
        if not order.order_date:
            continue
            
        days_overdue = (today - order.order_date).days
        
        # Categorize by age
        if days_overdue <= 30:
            category = "current"
        elif days_overdue <= 60:
            category = "30_days"
        elif days_overdue <= 90:
            category = "60_days"
        else:
            category = "90_plus_days"
        
        # Get supplier
        supplier = db.query(models.Supplier).filter(
            models.Supplier.id == order.supplier_id
        ).first()
        
        aging_data.append({
            "supplier_id": order.supplier_id,
            "supplier_name": supplier.supplier_name if supplier else "Unknown",
            "po_number": order.po_number,
            "order_date": order.order_date.isoformat(),
            "amount": float(order.total_amount),
            "days_overdue": days_overdue,
            "category": category
        })
    
    return aging_data

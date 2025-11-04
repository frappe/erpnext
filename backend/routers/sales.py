"""
Sales Management API Router

Handles customers, sales orders, invoices, and accounts receivable
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

router = APIRouter(prefix="/api/sales", tags=["sales"])


# ============================================================================
# CUSTOMER MANAGEMENT
# ============================================================================

@router.post("/customers", response_model=dict)
def create_customer(
    customer: schemas.CustomerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new customer"""
    
    # Check for duplicate customer code
    existing = db.query(models.Customer).filter(
        and_(
            models.Customer.company_id == current_user.company_id,
            models.Customer.customer_code == customer.customer_code
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Customer code already exists")
    
    # Create customer
    db_customer = models.Customer(
        company_id=current_user.company_id,
        **customer.dict()
    )
    
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    
    return {
        "id": db_customer.id,
        "customer_code": db_customer.customer_code,
        "customer_name": db_customer.customer_name,
        "message": "Customer created successfully"
    }


@router.get("/customers", response_model=List[dict])
def list_customers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all customers"""
    
    query = db.query(models.Customer).filter(
        models.Customer.company_id == current_user.company_id
    )
    
    if search:
        query = query.filter(
            or_(
                models.Customer.customer_name.ilike(f"%{search}%"),
                models.Customer.customer_code.ilike(f"%{search}%"),
                models.Customer.email.ilike(f"%{search}%")
            )
        )
    
    customers = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": c.id,
            "customer_code": c.customer_code,
            "customer_name": c.customer_name,
            "email": c.email,
            "phone": c.phone,
            "tax_id": c.tax_id,
            "credit_limit": float(c.credit_limit) if c.credit_limit else 0,
            "payment_terms_days": c.payment_terms_days,
            "is_active": c.is_active
        }
        for c in customers
    ]


@router.get("/customers/{customer_id}", response_model=dict)
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get customer details"""
    
    customer = db.query(models.Customer).filter(
        and_(
            models.Customer.id == customer_id,
            models.Customer.company_id == current_user.company_id
        )
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {
        "id": customer.id,
        "customer_code": customer.customer_code,
        "customer_name": customer.customer_name,
        "email": customer.email,
        "phone": customer.phone,
        "address": customer.address,
        "city": customer.city,
        "country": customer.country,
        "tax_id": customer.tax_id,
        "credit_limit": float(customer.credit_limit) if customer.credit_limit else 0,
        "payment_terms_days": customer.payment_terms_days,
        "is_active": customer.is_active,
        "created_at": customer.created_at.isoformat() if customer.created_at else None
    }


@router.put("/customers/{customer_id}", response_model=dict)
def update_customer(
    customer_id: str,
    customer_update: schemas.CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update customer"""
    
    db_customer = db.query(models.Customer).filter(
        and_(
            models.Customer.id == customer_id,
            models.Customer.company_id == current_user.company_id
        )
    ).first()
    
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    for key, value in customer_update.dict(exclude_unset=True).items():
        setattr(db_customer, key, value)
    
    db.commit()
    db.refresh(db_customer)
    
    return {"message": "Customer updated successfully"}


# ============================================================================
# SALES ORDERS
# ============================================================================

@router.post("/orders", response_model=dict)
def create_sales_order(
    order: schemas.SalesOrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new sales order"""
    
    # Verify customer exists
    customer = db.query(models.Customer).filter(
        and_(
            models.Customer.id == order.customer_id,
            models.Customer.company_id == current_user.company_id
        )
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Generate order number
    order_count = db.query(func.count(models.SalesOrder.id)).filter(
        models.SalesOrder.company_id == current_user.company_id
    ).scalar()
    order_number = f"SO-{date.today().strftime('%Y%m')}-{order_count + 1:05d}"
    
    # Calculate totals
    subtotal = sum(line.quantity * line.unit_price for line in order.lines)
    tax_amount = subtotal * Decimal(0.16)  # 16% VAT default
    total_amount = subtotal + tax_amount
    
    # Create sales order
    db_order = models.SalesOrder(
        company_id=current_user.company_id,
        order_number=order_number,
        customer_id=order.customer_id,
        order_date=order.order_date or date.today(),
        delivery_date=order.delivery_date,
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
        db_line = models.SalesOrderLine(
            sales_order_id=db_order.id,
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
        "order_number": db_order.order_number,
        "total_amount": float(db_order.total_amount),
        "status": db_order.status,
        "message": "Sales order created successfully"
    }


@router.get("/orders", response_model=List[dict])
def list_sales_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List sales orders"""
    
    query = db.query(models.SalesOrder).filter(
        models.SalesOrder.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.SalesOrder.status == status)
    
    if customer_id:
        query = query.filter(models.SalesOrder.customer_id == customer_id)
    
    orders = query.order_by(models.SalesOrder.order_date.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": o.id,
            "order_number": o.order_number,
            "customer_id": o.customer_id,
            "order_date": o.order_date.isoformat() if o.order_date else None,
            "delivery_date": o.delivery_date.isoformat() if o.delivery_date else None,
            "total_amount": float(o.total_amount),
            "currency": o.currency,
            "status": o.status
        }
        for o in orders
    ]


@router.get("/orders/{order_id}", response_model=dict)
def get_sales_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get sales order details with line items"""
    
    order = db.query(models.SalesOrder).filter(
        and_(
            models.SalesOrder.id == order_id,
            models.SalesOrder.company_id == current_user.company_id
        )
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")
    
    # Get customer
    customer = db.query(models.Customer).filter(models.Customer.id == order.customer_id).first()
    
    # Get order lines
    lines = db.query(models.SalesOrderLine).filter(
        models.SalesOrderLine.sales_order_id == order_id
    ).all()
    
    return {
        "id": order.id,
        "order_number": order.order_number,
        "customer": {
            "id": customer.id if customer else None,
            "name": customer.customer_name if customer else None,
            "code": customer.customer_code if customer else None
        },
        "order_date": order.order_date.isoformat() if order.order_date else None,
        "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None,
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


@router.post("/orders/{order_id}/confirm", response_model=dict)
def confirm_sales_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Confirm a sales order"""
    
    order = db.query(models.SalesOrder).filter(
        and_(
            models.SalesOrder.id == order_id,
            models.SalesOrder.company_id == current_user.company_id
        )
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")
    
    if order.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft orders can be confirmed")
    
    order.status = "confirmed"
    order.confirmed_date = datetime.utcnow()
    order.confirmed_by = current_user.id
    
    db.commit()
    
    return {"message": "Sales order confirmed successfully", "status": order.status}


# ============================================================================
# ACCOUNTS RECEIVABLE
# ============================================================================

@router.get("/receivables/aging", response_model=List[dict])
def get_ar_aging(
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get accounts receivable aging report"""
    
    query = db.query(models.SalesOrder).filter(
        and_(
            models.SalesOrder.company_id == current_user.company_id,
            models.SalesOrder.status.in_(["confirmed", "invoiced"]),
            models.SalesOrder.total_amount > 0
        )
    )
    
    if customer_id:
        query = query.filter(models.SalesOrder.customer_id == customer_id)
    
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
        
        # Get customer
        customer = db.query(models.Customer).filter(
            models.Customer.id == order.customer_id
        ).first()
        
        aging_data.append({
            "customer_id": order.customer_id,
            "customer_name": customer.customer_name if customer else "Unknown",
            "order_number": order.order_number,
            "order_date": order.order_date.isoformat(),
            "amount": float(order.total_amount),
            "days_overdue": days_overdue,
            "category": category
        })
    
    return aging_data

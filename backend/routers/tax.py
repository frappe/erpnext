"""
VAT/Tax Management API Router

Handles tax settings, tax calculations, and VAT returns
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, extract
from typing import List, Optional, Dict
from datetime import datetime, date
from decimal import Decimal
from dateutil.relativedelta import relativedelta

import models
import schemas
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/tax", tags=["tax"])


# ============================================================================
# TAX SETTINGS
# ============================================================================

@router.post("/settings", response_model=dict)
def create_tax_setting(
    tax: schemas.TaxSettingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new tax setting"""
    
    db_tax = models.TaxSetting(
        company_id=current_user.company_id,
        **tax.dict()
    )
    
    db.add(db_tax)
    db.commit()
    db.refresh(db_tax)
    
    return {
        "id": db_tax.id,
        "tax_type": db_tax.tax_type,
        "tax_name": db_tax.tax_name,
        "tax_rate": float(db_tax.tax_rate) if db_tax.tax_rate else None,
        "message": "Tax setting created successfully"
    }


@router.get("/settings", response_model=List[dict])
def list_tax_settings(
    tax_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List tax settings"""
    
    query = db.query(models.TaxSetting).filter(
        models.TaxSetting.company_id == current_user.company_id
    )
    
    if tax_type:
        query = query.filter(models.TaxSetting.tax_type == tax_type)
    
    if is_active is not None:
        query = query.filter(models.TaxSetting.is_active == is_active)
    
    tax_settings = query.all()
    
    return [
        {
            "id": t.id,
            "tax_type": t.tax_type,
            "tax_name": t.tax_name,
            "tax_jurisdiction": t.tax_jurisdiction,
            "tax_rate": float(t.tax_rate) if t.tax_rate else None,
            "effective_from": t.effective_from.isoformat() if t.effective_from else None,
            "effective_to": t.effective_to.isoformat() if t.effective_to else None,
            "filing_frequency": t.filing_frequency,
            "is_active": t.is_active
        }
        for t in tax_settings
    ]


@router.get("/settings/{tax_id}", response_model=dict)
def get_tax_setting(
    tax_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get tax setting details"""
    
    tax = db.query(models.TaxSetting).filter(
        and_(
            models.TaxSetting.id == tax_id,
            models.TaxSetting.company_id == current_user.company_id
        )
    ).first()
    
    if not tax:
        raise HTTPException(status_code=404, detail="Tax setting not found")
    
    return {
        "id": tax.id,
        "tax_type": tax.tax_type,
        "tax_name": tax.tax_name,
        "tax_jurisdiction": tax.tax_jurisdiction,
        "tax_rate": float(tax.tax_rate) if tax.tax_rate else None,
        "tax_brackets": tax.tax_brackets,
        "tax_payable_account_id": tax.tax_payable_account_id,
        "tax_expense_account_id": tax.tax_expense_account_id,
        "effective_from": tax.effective_from.isoformat() if tax.effective_from else None,
        "effective_to": tax.effective_to.isoformat() if tax.effective_to else None,
        "filing_frequency": tax.filing_frequency,
        "filing_due_day": tax.filing_due_day,
        "is_active": tax.is_active
    }


@router.put("/settings/{tax_id}", response_model=dict)
def update_tax_setting(
    tax_id: str,
    tax_update: schemas.TaxSettingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update tax setting"""
    
    db_tax = db.query(models.TaxSetting).filter(
        and_(
            models.TaxSetting.id == tax_id,
            models.TaxSetting.company_id == current_user.company_id
        )
    ).first()
    
    if not db_tax:
        raise HTTPException(status_code=404, detail="Tax setting not found")
    
    for key, value in tax_update.dict(exclude_unset=True).items():
        setattr(db_tax, key, value)
    
    db.commit()
    db.refresh(db_tax)
    
    return {"message": "Tax setting updated successfully"}


# ============================================================================
# TAX CALCULATIONS
# ============================================================================

@router.post("/calculate", response_model=dict)
def calculate_tax(
    calculation: schemas.TaxCalculation,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Calculate tax on an amount"""
    
    # Get tax setting
    tax_setting = db.query(models.TaxSetting).filter(
        and_(
            models.TaxSetting.id == calculation.tax_setting_id,
            models.TaxSetting.company_id == current_user.company_id,
            models.TaxSetting.is_active == True
        )
    ).first()
    
    if not tax_setting:
        raise HTTPException(status_code=404, detail="Tax setting not found")
    
    amount = Decimal(str(calculation.amount))
    
    # Simple flat rate calculation
    if tax_setting.tax_rate:
        tax_amount = amount * Decimal(str(tax_setting.tax_rate))
        total = amount + tax_amount
        
        return {
            "base_amount": float(amount),
            "tax_rate": float(tax_setting.tax_rate),
            "tax_amount": float(tax_amount),
            "total_amount": float(total),
            "tax_type": tax_setting.tax_type
        }
    
    # Progressive tax brackets (for PAYE)
    elif tax_setting.tax_brackets:
        # TODO: Implement progressive tax calculation
        return {
            "base_amount": float(amount),
            "tax_amount": 0.0,
            "total_amount": float(amount),
            "tax_type": tax_setting.tax_type,
            "note": "Progressive tax calculation not yet implemented"
        }
    
    return {
        "base_amount": float(amount),
        "tax_amount": 0.0,
        "total_amount": float(amount),
        "tax_type": tax_setting.tax_type
    }


# ============================================================================
# VAT RETURNS
# ============================================================================

@router.get("/vat-return", response_model=dict)
def generate_vat_return(
    start_date: date = Query(..., description="Return period start date"),
    end_date: date = Query(..., description="Return period end date"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Generate VAT return for a period"""
    
    # Get VAT setting
    vat_setting = db.query(models.TaxSetting).filter(
        and_(
            models.TaxSetting.company_id == current_user.company_id,
            models.TaxSetting.tax_type == "VAT",
            models.TaxSetting.is_active == True
        )
    ).first()
    
    if not vat_setting:
        raise HTTPException(status_code=404, detail="VAT setting not configured")
    
    vat_rate = Decimal(str(vat_setting.tax_rate)) if vat_setting.tax_rate else Decimal("0.16")
    
    # Calculate Output VAT (from sales)
    sales_orders = db.query(models.SalesOrder).filter(
        and_(
            models.SalesOrder.company_id == current_user.company_id,
            models.SalesOrder.order_date >= start_date,
            models.SalesOrder.order_date <= end_date,
            models.SalesOrder.status.in_(["confirmed", "invoiced", "delivered"])
        )
    ).all()
    
    output_vat = Decimal(0)
    gross_sales = Decimal(0)
    
    for order in sales_orders:
        gross_sales += order.total_amount or Decimal(0)
        output_vat += order.tax_amount or Decimal(0)
    
    # Calculate Input VAT (from purchases)
    purchase_orders = db.query(models.PurchaseOrder).filter(
        and_(
            models.PurchaseOrder.company_id == current_user.company_id,
            models.PurchaseOrder.order_date >= start_date,
            models.PurchaseOrder.order_date <= end_date,
            models.PurchaseOrder.status.in_(["approved", "received"])
        )
    ).all()
    
    input_vat = Decimal(0)
    gross_purchases = Decimal(0)
    
    for order in purchase_orders:
        gross_purchases += order.total_amount or Decimal(0)
        input_vat += order.tax_amount or Decimal(0)
    
    # Calculate net VAT payable/refundable
    net_vat = output_vat - input_vat
    
    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "vat_rate": float(vat_rate),
        "sales": {
            "gross_sales": float(gross_sales),
            "net_sales": float(gross_sales - output_vat),
            "output_vat": float(output_vat),
            "transaction_count": len(sales_orders)
        },
        "purchases": {
            "gross_purchases": float(gross_purchases),
            "net_purchases": float(gross_purchases - input_vat),
            "input_vat": float(input_vat),
            "transaction_count": len(purchase_orders)
        },
        "summary": {
            "output_vat": float(output_vat),
            "input_vat": float(input_vat),
            "net_vat_payable": float(net_vat),
            "status": "payable" if net_vat > 0 else "refundable" if net_vat < 0 else "nil"
        }
    }


# ============================================================================
# TAX REPORTS
# ============================================================================

@router.get("/reports/summary", response_model=dict)
def get_tax_summary(
    year: int = Query(default_factory=lambda: date.today().year),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get annual tax summary"""
    
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    # Get all sales for the year
    sales = db.query(
        func.sum(models.SalesOrder.subtotal).label("total_sales"),
        func.sum(models.SalesOrder.tax_amount).label("total_vat")
    ).filter(
        and_(
            models.SalesOrder.company_id == current_user.company_id,
            models.SalesOrder.order_date >= start_date,
            models.SalesOrder.order_date <= end_date
        )
    ).first()
    
    # Get all purchases for the year
    purchases = db.query(
        func.sum(models.PurchaseOrder.subtotal).label("total_purchases"),
        func.sum(models.PurchaseOrder.tax_amount).label("total_input_vat")
    ).filter(
        and_(
            models.PurchaseOrder.company_id == current_user.company_id,
            models.PurchaseOrder.order_date >= start_date,
            models.PurchaseOrder.order_date <= end_date
        )
    ).first()
    
    return {
        "year": year,
        "sales": {
            "total_sales": float(sales.total_sales or 0),
            "output_vat": float(sales.total_vat or 0)
        },
        "purchases": {
            "total_purchases": float(purchases.total_purchases or 0),
            "input_vat": float(purchases.total_input_vat or 0)
        },
        "net_vat": float((sales.total_vat or 0) - (purchases.total_input_vat or 0))
    }

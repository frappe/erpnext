from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from Goldfish.config import get_db
from Goldfish.models.sales_order import SalesOrder, SalesOrderItem
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter()

class SalesOrderItemCreate(BaseModel):
    item_code: str
    qty: float
    rate: float

class SalesOrderCreate(BaseModel):
    customer: str
    transaction_date: datetime
    delivery_date: datetime
    items: List[SalesOrderItemCreate]

@router.post("/sales-orders/", response_model=SalesOrderCreate)
def create_sales_order(sales_order: SalesOrderCreate, db: Session = Depends(get_db)):
    db_sales_order = SalesOrder(
        customer=sales_order.customer,
        transaction_date=sales_order.transaction_date,
        delivery_date=sales_order.delivery_date
    )
    db.add(db_sales_order)
    db.flush()  # This assigns an ID to db_sales_order

    for item in sales_order.items:
        db_item = SalesOrderItem(
            parent=db_sales_order.name,
            item_code=item.item_code,
            qty=item.qty,
            rate=item.rate,
            amount=item.qty * item.rate
        )
        db.add(db_item)

    db_sales_order.total = sum(item.qty * item.rate for item in sales_order.items)
    db.commit()
    db.refresh(db_sales_order)
    return db_sales_order

@router.get("/sales-orders/{sales_order_id}")
def read_sales_order(sales_order_id: str, db: Session = Depends(get_db)):
    sales_order = db.query(SalesOrder).filter(SalesOrder.name == sales_order_id).first()
    if sales_order is None:
        raise HTTPException(status_code=404, detail="Sales Order not found")
    return sales_order

# Add more CRUD operations as needed
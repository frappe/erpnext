from sqlalchemy.orm import Session
from Goldfish.models.sales_order import SalesOrder, SalesOrderItem
from Goldfish.models.item import Item
from typing import List
from Goldfish.utils.exceptions import ValidationError, NotFoundError

def validate_sales_order(db: Session, sales_order: SalesOrder):
    if not sales_order.items:
        raise ValidationError("Sales Order must have at least one item")

    for item in sales_order.items:
        db_item = db.query(Item).filter(Item.item_code == item.item_code).first()
        if not db_item:
            raise NotFoundError(f"Item {item.item_code} not found")
        
        if item.qty <= 0:
            raise ValidationError(f"Quantity for item {item.item_code} must be greater than zero")
        
        if item.rate <= 0:
            raise ValidationError(f"Rate for item {item.item_code} must be greater than zero")

def create_sales_order(db: Session, customer: str, transaction_date: datetime, items: List[SalesOrderItem]) -> SalesOrder:
    sales_order = SalesOrder(
        customer=customer,
        transaction_date=transaction_date,
        status="Draft"
    )
    db.add(sales_order)
    db.flush()

    for item in items:
        db_item = SalesOrderItem(
            parent=sales_order.name,
            item_code=item.item_code,
            qty=item.qty,
            rate=item.rate,
            amount=item.qty * item.rate
        )
        db.add(db_item)

    validate_sales_order(db, sales_order)
    update_sales_order_total(db, sales_order)
    db.commit()
    return sales_order

def update_sales_order_total(db: Session, sales_order: SalesOrder):
    total_amount = sum(item.amount for item in sales_order.items)
    sales_order.total = total_amount
    db.commit()

def get_sales_order_status(db: Session, sales_order_id: str) -> str:
    sales_order = db.query(SalesOrder).filter(SalesOrder.name == sales_order_id).first()
    if not sales_order:
        raise NotFoundError(f"Sales Order {sales_order_id} not found")
    return sales_order.status
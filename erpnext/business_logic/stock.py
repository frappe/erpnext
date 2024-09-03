from sqlalchemy.orm import Session
from Goldfish.models.stock import StockEntry, StockEntryDetail
from Goldfish.models.item import Item
from typing import List
from Goldfish.utils.exceptions import ValidationError, NotFoundError, InsufficientStockError

def update_stock_balances(db: Session, stock_entry: StockEntry):
    for item in stock_entry.items:
        db_item = db.query(Item).filter(Item.item_code == item.item_code).first()
        if not db_item:
            raise NotFoundError(f"Item {item.item_code} not found")

        if stock_entry.purpose == "Material Receipt":
            db_item.stock_qty += item.qty
        elif stock_entry.purpose == "Material Issue":
            if db_item.stock_qty < item.qty:
                raise InsufficientStockError(f"Insufficient stock for item {item.item_code}")
            db_item.stock_qty -= item.qty
        elif stock_entry.purpose == "Material Transfer":
            # Implement logic for material transfer between warehouses
            pass

    db.commit()

def validate_stock_entry(db: Session, stock_entry: StockEntry):
    if not stock_entry.items:
        raise ValidationError("Stock Entry must have at least one item")

    for item in stock_entry.items:
        if item.qty <= 0:
            raise ValidationError(f"Quantity for item {item.item_code} must be greater than zero")

        db_item = db.query(Item).filter(Item.item_code == item.item_code).first()
        if not db_item:
            raise NotFoundError(f"Item {item.item_code} not found")

    if stock_entry.purpose not in ["Material Receipt", "Material Issue", "Material Transfer"]:
        raise ValidationError("Invalid Stock Entry purpose")

def create_stock_entry(db: Session, purpose: str, items: List[StockEntryDetail]) -> StockEntry:
    stock_entry = StockEntry(purpose=purpose)
    db.add(stock_entry)
    db.flush()

    for item in items:
        db_item = StockEntryDetail(
            parent=stock_entry.name,
            item_code=item.item_code,
            qty=item.qty,
            basic_rate=item.basic_rate
        )
        db.add(db_item)

    validate_stock_entry(db, stock_entry)
    update_stock_balances(db, stock_entry)
    db.commit()
    return stock_entry

def get_item_stock_balance(db: Session, item_code: str) -> float:
    item = db.query(Item).filter(Item.item_code == item_code).first()
    if not item:
        raise ValueError(f"Item {item_code} not found")
    return item.stock_qty
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from Goldfish.config import get_db
from Goldfish.models.stock import StockEntry, StockEntryDetail, PurchaseReceipt, PurchaseReceiptItem
from Goldfish.auth.jwt import verify_token
from Goldfish.models.user import User
from pydantic import BaseModel
from typing import List
from datetime import datetime
from Goldfish.auth.rbac import has_permission
from Goldfish.utils.exceptions import ValidationError, NotFoundError, InsufficientStockError
from Goldfish.tasks import process_stock_entry

router = APIRouter()

class StockEntryDetailCreate(BaseModel):
    item_code: str
    qty: float
    basic_rate: float

class StockEntryCreate(BaseModel):
    posting_date: datetime
    company: str
    purpose: str
    items: List[StockEntryDetailCreate]

@router.post("/stock-entries/", response_model=StockEntryCreate)
def create_stock_entry(
    stock_entry: StockEntryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    try:
        db_stock_entry = StockEntry(
            posting_date=stock_entry.posting_date,
            company=stock_entry.company,
            purpose=stock_entry.purpose
        )
        db.add(db_stock_entry)
        db.flush()

        for item in stock_entry.items:
            db_item = StockEntryDetail(
                parent=db_stock_entry.name,
                item_code=item.item_code,
                qty=item.qty,
                basic_rate=item.basic_rate
            )
            db.add(db_item)

        db.commit()
        db.refresh(db_stock_entry)
        
        # Schedule the stock entry processing as a background task
        background_tasks.add_task(process_stock_entry.delay, db_stock_entry.name)
        
        return db_stock_entry
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientStockError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stock-entries/{stock_entry_id}")
def read_stock_entry(stock_entry_id: str, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    stock_entry = db.query(StockEntry).filter(StockEntry.name == stock_entry_id).first()
    if stock_entry is None:
        raise HTTPException(status_code=404, detail="Stock Entry not found")
    return stock_entry

# Add more CRUD operations for stock entries and purchase receipts
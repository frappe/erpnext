from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from Goldfish.config import get_db
from Goldfish.models.sales_order import SalesOrder, SalesOrderItem
from Goldfish.auth.jwt import verify_token
from Goldfish.models.user import User
from pydantic import BaseModel
from typing import List
from datetime import datetime
from Goldfish.utils.exceptions import ValidationError, NotFoundError

router = APIRouter()

class SalesOrderItemCreate(BaseModel):
    item_code: str
    qty: float
    rate: float

class SalesOrderCreate(BaseModel):
    customer: str
    transaction_date: datetime
    items: List[SalesOrderItemCreate]

@router.post("/sales-orders/", response_model=SalesOrderCreate)
def create_sales_order_api(sales_order: SalesOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    try:
        db_sales_order = create_sales_order(db, sales_order.customer, sales_order.transaction_date, sales_order.items)
        return db_sales_order
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sales-orders/{sales_order_id}/status")
def get_sales_order_status_api(sales_order_id: str, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    try:
        status = get_sales_order_status(db, sales_order_id)
        return {"sales_order_id": sales_order_id, "status": status}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
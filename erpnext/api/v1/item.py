from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from Goldfish.config import get_db
from Goldfish.models.item import Item
from Goldfish.auth.jwt import verify_token
from Goldfish.models.user import User
from pydantic import BaseModel
from Goldfish.utils.exceptions import ValidationError, NotFoundError

router = APIRouter()

class ItemCreate(BaseModel):
    item_code: str
    item_name: str
    item_group: str
    stock_uom: str
    is_stock_item: bool = True
    description: str = None

@router.post("/items/", response_model=ItemCreate)
def create_item(item: ItemCreate, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    try:
        db_item = Item(**item.dict())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/items/{item_code}")
def read_item(item_code: str, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    item = db.query(Item).filter(Item.item_code == item_code).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

# Add more CRUD operations as needed, all with the verify_token dependency
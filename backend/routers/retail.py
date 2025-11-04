from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Store, POSSale
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/retail", tags=["retail"])

# Stores
@router.post("/stores")
async def create_store(
    store: StoreCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_store = Store(**store.dict(), company_id=current_user.company_id)
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store

@router.get("/stores")
async def get_stores(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Store).filter(Store.company_id == current_user.company_id).all()

@router.put("/stores/{store_id}")
async def update_store(
    store_id: str,
    store_update: StoreCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    store = db.query(Store).filter(
        Store.id == store_id,
        Store.company_id == current_user.company_id
    ).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    for key, value in store_update.dict().items():
        setattr(store, key, value)
    
    db.commit()
    db.refresh(store)
    return store

@router.delete("/stores/{store_id}")
async def delete_store(
    store_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    store = db.query(Store).filter(
        Store.id == store_id,
        Store.company_id == current_user.company_id
    ).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    db.delete(store)
    db.commit()
    return {"message": "Store deleted successfully"}

# POS Sales
@router.post("/sales")
async def create_pos_sale(
    sale: POSSaleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_sale = POSSale(**sale.dict(), company_id=current_user.company_id)
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)
    return db_sale

@router.get("/sales")
async def get_pos_sales(
    store_id: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(POSSale).filter(POSSale.company_id == current_user.company_id)
    if store_id:
        query = query.filter(POSSale.store_id == store_id)
    return query.all()

@router.get("/sales/{sale_id}")
async def get_pos_sale(
    sale_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    sale = db.query(POSSale).filter(
        POSSale.id == sale_id,
        POSSale.company_id == current_user.company_id
    ).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale

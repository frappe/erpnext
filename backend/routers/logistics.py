from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import LogisticsWarehouse, LogisticsShipment
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/logistics", tags=["logistics"])

# Warehouses
@router.post("/warehouses")
async def create_warehouse(
    warehouse: schemas.WarehouseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_warehouse = LogisticsWarehouse(**warehouse.dict(), company_id=current_user.company_id)
    db.add(db_warehouse)
    db.commit()
    db.refresh(db_warehouse)
    return db_warehouse

@router.get("/warehouses")
async def get_warehouses(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(LogisticsWarehouse).filter(
        LogisticsWarehouse.company_id == current_user.company_id
    ).all()

@router.get("/warehouses/{warehouse_id}")
async def get_warehouse(
    warehouse_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    warehouse = db.query(LogisticsWarehouse).filter(
        LogisticsWarehouse.id == warehouse_id,
        LogisticsWarehouse.company_id == current_user.company_id
    ).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse

@router.put("/warehouses/{warehouse_id}")
async def update_warehouse(
    warehouse_id: str,
    warehouse_update: schemas.WarehouseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    warehouse = db.query(LogisticsWarehouse).filter(
        LogisticsWarehouse.id == warehouse_id,
        LogisticsWarehouse.company_id == current_user.company_id
    ).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    for key, value in warehouse_update.dict(exclude_unset=True).items():
        setattr(warehouse, key, value)
    
    db.commit()
    db.refresh(warehouse)
    return warehouse

@router.delete("/warehouses/{warehouse_id}")
async def delete_warehouse(
    warehouse_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    warehouse = db.query(LogisticsWarehouse).filter(
        LogisticsWarehouse.id == warehouse_id,
        LogisticsWarehouse.company_id == current_user.company_id
    ).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    db.delete(warehouse)
    db.commit()
    return {"message": "Warehouse deleted successfully"}

# Shipments
@router.post("/shipments")
async def create_shipment(
    shipment: schemas.ShipmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_shipment = LogisticsShipment(**shipment.dict(), company_id=current_user.company_id)
    db.add(db_shipment)
    db.commit()
    db.refresh(db_shipment)
    return db_shipment

@router.get("/shipments")
async def get_shipments(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(LogisticsShipment).filter(
        LogisticsShipment.company_id == current_user.company_id
    ).all()

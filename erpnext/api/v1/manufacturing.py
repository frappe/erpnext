from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from Goldfish.config import get_db
from Goldfish.models.manufacturing import WorkOrder, WorkOrderOperation, BOM, BOMItem
from Goldfish.auth.jwt import verify_token
from Goldfish.models.user import User
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from Goldfish.utils.exceptions import ValidationError, NotFoundError, InsufficientStockError, WorkflowError
from Goldfish.tasks import complete_work_order_task

router = APIRouter()

# Work Order API
class WorkOrderOperationCreate(BaseModel):
    operation: str
    workstation: str
    time_in_mins: float

class WorkOrderCreate(BaseModel):
    production_item: str
    qty: float
    planned_start_date: datetime
    operations: List[WorkOrderOperationCreate]
    attachment_url: Optional[str] = None

class WorkOrderUpdate(BaseModel):
    qty: Optional[float]
    planned_start_date: Optional[datetime]
    status: Optional[str]

@router.post("/work-orders/", response_model=WorkOrderCreate)
async def create_work_order(
    work_order: WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    try:
        db_work_order = WorkOrder(**work_order.dict(exclude={'operations'}))
        db.add(db_work_order)
        db.flush()

        for operation in work_order.operations:
            db_operation = WorkOrderOperation(
                parent=db_work_order.name,
                **operation.dict()
            )
            db.add(db_operation)

        validate_work_order(db, db_work_order)
        calculate_work_order_times(db, db_work_order)
        db.commit()
        return db_work_order
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.get("/work-orders/{work_order_id}")
def read_work_order(work_order_id: str, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    work_order = db.query(WorkOrder).filter(WorkOrder.name == work_order_id).first()
    if work_order is None:
        raise HTTPException(status_code=404, detail="Work Order not found")
    return work_order

@router.put("/work-orders/{work_order_id}")
def update_work_order(work_order_id: str, work_order: WorkOrderUpdate, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    db_work_order = db.query(WorkOrder).filter(WorkOrder.name == work_order_id).first()
    if db_work_order is None:
        raise HTTPException(status_code=404, detail="Work Order not found")
    for key, value in work_order.dict(exclude_unset=True).items():
        setattr(db_work_order, key, value)
    try:
        validate_work_order(db, db_work_order)
        calculate_work_order_times(db, db_work_order)
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return db_work_order

@router.delete("/work-orders/{work_order_id}")
def delete_work_order(work_order_id: str, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    db_work_order = db.query(WorkOrder).filter(WorkOrder.name == work_order_id).first()
    if db_work_order is None:
        raise HTTPException(status_code=404, detail="Work Order not found")
    db.delete(db_work_order)
    db.commit()
    return {"message": "Work Order deleted successfully"}

# BOM API
class BOMItemCreate(BaseModel):
    item_code: str
    qty: float
    rate: float

class BOMCreate(BaseModel):
    item: str
    quantity: float
    is_active: bool = True
    items: List[BOMItemCreate]

class BOMUpdate(BaseModel):
    quantity: Optional[float]
    is_active: Optional[bool]

@router.post("/boms/", response_model=BOMCreate)
def create_bom(bom: BOMCreate, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    try:
        db_bom = BOM(
            item=bom.item,
            quantity=bom.quantity,
            is_active=bom.is_active
        )
        db.add(db_bom)
        db.flush()

        for item in bom.items:
            db_item = BOMItem(
                parent=db_bom.name,
                item_code=item.item_code,
                qty=item.qty,
                rate=item.rate
            )
            db.add(db_item)

        validate_bom(db, db_bom)
        calculate_bom_cost(db, db_bom)
        db.commit()
        return db_bom
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/boms/{bom_id}")
def read_bom(bom_id: str, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    bom = db.query(BOM).filter(BOM.name == bom_id).first()
    if bom is None:
        raise HTTPException(status_code=404, detail="BOM not found")
    return bom

@router.put("/boms/{bom_id}")
def update_bom(bom_id: str, bom: BOMUpdate, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    db_bom = db.query(BOM).filter(BOM.name == bom_id).first()
    if db_bom is None:
        raise HTTPException(status_code=404, detail="BOM not found")
    for key, value in bom.dict(exclude_unset=True).items():
        setattr(db_bom, key, value)
    try:
        validate_bom(db, db_bom)
        calculate_bom_cost(db, db_bom)
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return db_bom

@router.delete("/boms/{bom_id}")
def delete_bom(bom_id: str, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    db_bom = db.query(BOM).filter(BOM.name == bom_id).first()
    if db_bom is None:
        raise HTTPException(status_code=404, detail="BOM not found")
    db.delete(db_bom)
    db.commit()
    return {"message": "BOM deleted successfully"}

@router.post("/work-orders/from-bom/{bom_id}")
def create_work_order_from_bom_api(bom_id: str, qty: float, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    try:
        work_order = create_work_order_from_bom(db, bom_id, qty)
        return work_order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/work-orders/{work_order_id}/complete")
def complete_work_order_api(
    work_order_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    work_order = db.query(WorkOrder).filter(WorkOrder.name == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="Work Order not found")
    
    if work_order.status == "Completed":
        raise HTTPException(status_code=400, detail="Work Order is already completed")
    
    # Schedule the work order completion as a background task
    background_tasks.add_task(complete_work_order_task.delay, work_order_id)
    
    return {"message": "Work Order completion process started"}
from sqlalchemy.orm import Session
from Goldfish.models.manufacturing import WorkOrder, WorkOrderOperation, BOM, BOMItem
from Goldfish.models.item import Item
from datetime import datetime, timedelta
from Goldfish.utils.exceptions import ValidationError, NotFoundError, InsufficientStockError, WorkflowError

def validate_work_order(db: Session, work_order: WorkOrder):
    if work_order.qty <= 0:
        raise ValidationError("Quantity must be greater than zero")
    
    if work_order.planned_start_date >= work_order.planned_end_date:
        raise ValidationError("Planned start date must be before planned end date")
    
    production_item = db.query(Item).filter(Item.item_code == work_order.production_item).first()
    if not production_item:
        raise NotFoundError(f"Production item not found: {work_order.production_item}")
    
    if not work_order.operations:
        raise ValidationError("Work order must have at least one operation")

def calculate_work_order_times(db: Session, work_order: WorkOrder):
    total_time = sum(operation.time_in_mins for operation in work_order.operations)
    work_order.planned_end_date = work_order.planned_start_date + timedelta(minutes=total_time)
    db.commit()

def validate_bom(db: Session, bom: BOM):
    if bom.quantity <= 0:
        raise ValueError("BOM quantity must be greater than zero")
    
    if not bom.items:
        raise ValueError("BOM must have at least one item")
    
    for item in bom.items:
        db_item = db.query(Item).filter(Item.item_code == item.item_code).first()
        if not db_item:
            raise ValueError(f"Item not found in BOM: {item.item_code}")
        
        if item.qty <= 0:
            raise ValueError(f"Quantity must be greater than zero for item: {item.item_code}")

def calculate_bom_cost(db: Session, bom: BOM):
    total_cost = sum(item.qty * item.rate for item in bom.items)
    bom.total_cost = total_cost
    db.commit()

def create_work_order_from_bom(db: Session, bom_id: str, qty: float) -> WorkOrder:
    bom = db.query(BOM).filter(BOM.name == bom_id).first()
    if not bom:
        raise NotFoundError(f"BOM not found: {bom_id}")
    
    work_order = WorkOrder(
        production_item=bom.item,
        qty=qty,
        planned_start_date=datetime.now(),
        status="Draft"
    )
    db.add(work_order)
    db.flush()
    
    for bom_item in bom.items:
        work_order_item = WorkOrderOperation(
            parent=work_order.name,
            item_code=bom_item.item_code,
            required_qty=bom_item.qty * (qty / bom.quantity),
            transferred_qty=0,
            consumed_qty=0
        )
        db.add(work_order_item)
    
    calculate_work_order_times(db, work_order)
    db.commit()
    return work_order

def update_work_order_status(db: Session, work_order: WorkOrder):
    total_qty = work_order.qty
    produced_qty = sum(item.consumed_qty for item in work_order.operations)
    
    if produced_qty == 0:
        work_order.status = "Not Started"
    elif produced_qty < total_qty:
        work_order.status = "In Process"
    elif produced_qty == total_qty:
        work_order.status = "Completed"
    else:
        raise ValueError("Produced quantity cannot exceed total quantity")
    
    db.commit()

def check_material_availability(db: Session, work_order: WorkOrder) -> bool:
    for operation in work_order.operations:
        item = db.query(Item).filter(Item.item_code == operation.item_code).first()
        if not item or item.stock_qty < operation.required_qty:
            return False
    return True

def consume_materials(db: Session, work_order: WorkOrder, qty_to_consume: float):
    if not check_material_availability(db, work_order):
        raise InsufficientStockError("Insufficient materials to consume")
    
    for operation in work_order.operations:
        item = db.query(Item).filter(Item.item_code == operation.item_code).first()
        consume_qty = operation.required_qty * (qty_to_consume / work_order.qty)
        item.stock_qty -= consume_qty
        operation.consumed_qty += consume_qty
    
    update_work_order_status(db, work_order)
    db.commit()

def complete_work_order(db: Session, work_order: WorkOrder):
    if work_order.status == "Completed":
        raise WorkflowError("Work order is already completed")
    
    remaining_qty = work_order.qty - sum(operation.consumed_qty for operation in work_order.operations)
    if remaining_qty > 0:
        consume_materials(db, work_order, remaining_qty)
    
    work_order.status = "Completed"
    work_order.actual_end_date = datetime.now()
    
    # Increase stock of produced item
    produced_item = db.query(Item).filter(Item.item_code == work_order.production_item).first()
    produced_item.stock_qty += work_order.qty
    
    db.commit()
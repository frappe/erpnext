from .celery_config import app
from sqlalchemy.orm import Session
from Goldfish.config import get_db
from Goldfish.models.stock import StockEntry
from Goldfish.business_logic.stock import update_stock_balances
from Goldfish.models.manufacturing import WorkOrder
from Goldfish.business_logic.manufacturing import complete_work_order
from Goldfish.utils.pdf_generator import generate_pdf

@app.task
def process_stock_entry(stock_entry_id: str):
    db: Session = next(get_db())
    try:
        stock_entry = db.query(StockEntry).filter(StockEntry.name == stock_entry_id).first()
        if stock_entry:
            update_stock_balances(db, stock_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

@app.task
def complete_work_order_task(work_order_id: str):
    db: Session = next(get_db())
    try:
        work_order = db.query(WorkOrder).filter(WorkOrder.name == work_order_id).first()
        if work_order:
            complete_work_order(db, work_order)
        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

@app.task
def generate_report_pdf(report_type: str, filters: dict, file_path: str):
    try:
        generate_pdf(report_type, filters, file_path)
    except Exception as e:
        raise
from .celery_config import app
from sqlalchemy.orm import Session
from goldfish.config import get_db
from goldfish.models.stock import StockEntry
from goldfish.business_logic.stock import update_stock_balances
from goldfish.models.manufacturing import WorkOrder
from goldfish.business_logic.manufacturing import complete_work_order
from goldfish.utils.pdf_generator import generate_pdf

# ... (rest of the file remains the same, just replace 'erpnext' with 'goldfish' in imports)
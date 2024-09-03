from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from goldfish.config import get_db
from goldfish.models.stock import StockEntry, StockEntryDetail, PurchaseReceipt, PurchaseReceiptItem
from goldfish.auth.jwt import verify_token
from goldfish.models.user import User
from pydantic import BaseModel
from typing import List
from datetime import datetime
from goldfish.auth.rbac import has_permission
from goldfish.utils.exceptions import ValidationError, NotFoundError, InsufficientStockError
from goldfish.tasks import process_stock_entry

# ... (rest of the file remains the same)
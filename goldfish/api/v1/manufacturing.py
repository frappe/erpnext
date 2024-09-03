from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from goldfish.config import get_db
from goldfish.models.manufacturing import WorkOrder, WorkOrderOperation, BOM, BOMItem
from goldfish.auth.jwt import verify_token
from goldfish.models.user import User
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from goldfish.utils.exceptions import ValidationError, NotFoundError, InsufficientStockError, WorkflowError
from goldfish.tasks import complete_work_order_task

# ... (rest of the file remains the same)
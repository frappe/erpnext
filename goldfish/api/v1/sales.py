from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from goldfish.config import get_db
from goldfish.models.sales_order import SalesOrder, SalesOrderItem
from goldfish.auth.jwt import verify_token
from goldfish.models.user import User
from pydantic import BaseModel
from typing import List
from datetime import datetime
from goldfish.utils.exceptions import ValidationError, NotFoundError

# ... (rest of the file remains the same)
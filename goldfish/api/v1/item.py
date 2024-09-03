from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from goldfish.config import get_db
from goldfish.models.item import Item
from goldfish.auth.jwt import verify_token
from goldfish.models.user import User
from pydantic import BaseModel
from goldfish.utils.exceptions import ValidationError, NotFoundError

# ... (rest of the file remains the same)
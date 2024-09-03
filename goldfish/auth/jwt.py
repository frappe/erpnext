from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from goldfish.config import settings
from goldfish.models.user import User
from goldfish.config import get_db

# ... (rest of the file remains the same)
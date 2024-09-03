from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from goldfish.config import get_db
from goldfish.models.crm import Lead, Opportunity, OpportunityItem
from goldfish.business_logic.crm import validate_lead, convert_lead_to_opportunity, validate_opportunity, update_opportunity_amount
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from goldfish.utils.exceptions import ValidationError, NotFoundError
from goldfish.auth.jwt import verify_token
from goldfish.models.user import User

# ... (rest of the file remains the same)
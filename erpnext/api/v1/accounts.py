from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from Goldfish.config import get_db
from Goldfish.models.accounts import Account, JournalEntry, JournalEntryAccount
from Goldfish.auth.jwt import verify_token
from Goldfish.models.user import User
from pydantic import BaseModel
from typing import List
from datetime import datetime
from Goldfish.utils.exceptions import ValidationError, NotFoundError

router = APIRouter()

class JournalEntryCreate(BaseModel):
    posting_date: datetime
    company: str
    accounts: List[JournalEntryAccount]

@router.post("/journal-entries/", response_model=JournalEntryCreate)
def create_journal_entry_api(journal_entry: JournalEntryCreate, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    try:
        db_journal_entry = create_journal_entry(db, journal_entry.posting_date, journal_entry.company, journal_entry.accounts)
        return db_journal_entry
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/accounts/{account_name}/balance")
def get_account_balance_api(account_name: str, db: Session = Depends(get_db), current_user: User = Depends(verify_token)):
    try:
        balance = get_account_balance(db, account_name)
        return {"account": account_name, "balance": balance}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Add more endpoints as needed, all with the verify_token dependency
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import LegalCase, LegalDocument
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/legal", tags=["legal"])

# Cases
@router.post("/cases")
async def create_case(
    case: schemas.LegalCaseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_case = LegalCase(**case.dict(), company_id=current_user.company_id)
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@router.get("/cases")
async def get_cases(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(LegalCase).filter(
        LegalCase.company_id == current_user.company_id
    ).all()

@router.get("/cases/{case_id}")
async def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    case = db.query(LegalCase).filter(
        LegalCase.id == case_id,
        LegalCase.company_id == current_user.company_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.put("/cases/{case_id}")
async def update_case(
    case_id: str,
    case_update: schemas.LegalCaseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    case = db.query(LegalCase).filter(
        LegalCase.id == case_id,
        LegalCase.company_id == current_user.company_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    for key, value in case_update.dict(exclude_unset=True).items():
        setattr(case, key, value)
    
    db.commit()
    db.refresh(case)
    return case

@router.delete("/cases/{case_id}")
async def delete_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    case = db.query(LegalCase).filter(
        LegalCase.id == case_id,
        LegalCase.company_id == current_user.company_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    db.delete(case)
    db.commit()
    return {"message": "Case deleted successfully"}

# Documents
@router.post("/documents")
async def create_document(
    document: schemas.LegalDocumentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_document = LegalDocument(**document.dict(), company_id=current_user.company_id)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

@router.get("/documents")
async def get_documents(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(LegalDocument).filter(
        LegalDocument.company_id == current_user.company_id
    ).all()

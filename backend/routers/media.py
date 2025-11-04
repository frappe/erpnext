from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import MediaContent, MediaPublication
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/media", tags=["media"])

# Content
@router.post("/content")
async def create_content(
    content: schemas.ContentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_content = MediaContent(**content.dict(), company_id=current_user.company_id)
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    return db_content

@router.get("/content")
async def get_contents(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(MediaContent).filter(
        MediaContent.company_id == current_user.company_id
    ).all()

@router.get("/content/{content_id}")
async def get_content(
    content_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    content = db.query(MediaContent).filter(
        MediaContent.id == content_id,
        MediaContent.company_id == current_user.company_id
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content

@router.put("/content/{content_id}")
async def update_content(
    content_id: str,
    content_update: schemas.ContentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    content = db.query(MediaContent).filter(
        MediaContent.id == content_id,
        MediaContent.company_id == current_user.company_id
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    for key, value in content_update.dict(exclude_unset=True).items():
        setattr(content, key, value)
    
    db.commit()
    db.refresh(content)
    return content

@router.delete("/content/{content_id}")
async def delete_content(
    content_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    content = db.query(MediaContent).filter(
        MediaContent.id == content_id,
        MediaContent.company_id == current_user.company_id
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    db.delete(content)
    db.commit()
    return {"message": "Content deleted successfully"}

# Publications
@router.post("/publications")
async def create_publication(
    publication: schemas.PublicationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_publication = MediaPublication(**publication.dict(), company_id=current_user.company_id)
    db.add(db_publication)
    db.commit()
    db.refresh(db_publication)
    return db_publication

@router.get("/publications")
async def get_publications(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(MediaPublication).filter(
        MediaPublication.company_id == current_user.company_id
    ).all()

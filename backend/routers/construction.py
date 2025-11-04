from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import ConstructionProject, BillOfQuantities
import schemas
from auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/api/construction", tags=["construction"])

# Construction Projects
@router.post("/projects")
async def create_project(
    project: schemas.ConstructionProjectCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_project = ConstructionProject(
        **project.dict(),
        company_id=current_user.company_id
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("/projects")
async def get_projects(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(ConstructionProject).filter(
        ConstructionProject.company_id == current_user.company_id
    ).all()

@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    project = db.query(ConstructionProject).filter(
        ConstructionProject.id == project_id,
        ConstructionProject.company_id == current_user.company_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    project_update: schemas.ConstructionProjectCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    project = db.query(ConstructionProject).filter(
        ConstructionProject.id == project_id,
        ConstructionProject.company_id == current_user.company_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    for key, value in project_update.dict().items():
        setattr(project, key, value)
    
    db.commit()
    db.refresh(project)
    return project

@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    project = db.query(ConstructionProject).filter(
        ConstructionProject.id == project_id,
        ConstructionProject.company_id == current_user.company_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

# Bill of Quantities
@router.post("/boq")
async def create_boq(
    boq: schemas.BillOfQuantitiesCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    amount = (boq.quantity or 0) * (boq.rate or 0)
    db_boq = BillOfQuantities(
        **boq.dict(),
        company_id=current_user.company_id,
        amount=amount
    )
    db.add(db_boq)
    db.commit()
    db.refresh(db_boq)
    return db_boq

@router.get("/boq")
async def get_boq(
    project_id: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(BillOfQuantities).filter(
        BillOfQuantities.company_id == current_user.company_id
    )
    if project_id:
        query = query.filter(BillOfQuantities.project_id == project_id)
    return query.all()

@router.delete("/boq/{boq_id}")
async def delete_boq(
    boq_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    boq = db.query(BillOfQuantities).filter(
        BillOfQuantities.id == boq_id,
        BillOfQuantities.company_id == current_user.company_id
    ).first()
    if not boq:
        raise HTTPException(status_code=404, detail="BOQ item not found")
    
    db.delete(boq)
    db.commit()
    return {"message": "BOQ item deleted successfully"}

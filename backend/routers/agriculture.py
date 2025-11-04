from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Farm, CropPlanting, Livestock
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/agriculture", tags=["agriculture"])

# Farms
@router.post("/farms")
async def create_farm(
    farm: schemas.FarmCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_farm = Farm(**farm.dict(), company_id=current_user.company_id)
    db.add(db_farm)
    db.commit()
    db.refresh(db_farm)
    return db_farm

@router.get("/farms")
async def get_farms(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Farm).filter(Farm.company_id == current_user.company_id).all()

@router.put("/farms/{farm_id}")
async def update_farm(
    farm_id: str,
    farm_update: schemas.FarmCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    farm = db.query(Farm).filter(
        Farm.id == farm_id,
        Farm.company_id == current_user.company_id
    ).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    
    for key, value in farm_update.dict().items():
        setattr(farm, key, value)
    
    db.commit()
    db.refresh(farm)
    return farm

@router.delete("/farms/{farm_id}")
async def delete_farm(
    farm_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    farm = db.query(Farm).filter(
        Farm.id == farm_id,
        Farm.company_id == current_user.company_id
    ).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    
    db.delete(farm)
    db.commit()
    return {"message": "Farm deleted successfully"}

# Crop Plantings
@router.post("/crops")
async def create_crop_planting(
    crop: schemas.CropPlantingCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_crop = CropPlanting(**crop.dict(), company_id=current_user.company_id)
    db.add(db_crop)
    db.commit()
    db.refresh(db_crop)
    return db_crop

@router.get("/crops")
async def get_crop_plantings(
    farm_id: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(CropPlanting).filter(
        CropPlanting.company_id == current_user.company_id
    )
    if farm_id:
        query = query.filter(CropPlanting.farm_id == farm_id)
    return query.all()

@router.put("/crops/{crop_id}")
async def update_crop_planting(
    crop_id: str,
    crop_update: schemas.CropPlantingCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    crop = db.query(CropPlanting).filter(
        CropPlanting.id == crop_id,
        CropPlanting.company_id == current_user.company_id
    ).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop planting not found")
    
    for key, value in crop_update.dict().items():
        setattr(crop, key, value)
    
    db.commit()
    db.refresh(crop)
    return crop

@router.delete("/crops/{crop_id}")
async def delete_crop_planting(
    crop_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    crop = db.query(CropPlanting).filter(
        CropPlanting.id == crop_id,
        CropPlanting.company_id == current_user.company_id
    ).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop planting not found")
    
    db.delete(crop)
    db.commit()
    return {"message": "Crop planting deleted successfully"}

# Livestock
@router.post("/livestock")
async def create_livestock(
    livestock: schemas.LivestockCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_livestock = Livestock(**livestock.dict(), company_id=current_user.company_id)
    db.add(db_livestock)
    db.commit()
    db.refresh(db_livestock)
    return db_livestock

@router.get("/livestock")
async def get_livestock(
    farm_id: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Livestock).filter(
        Livestock.company_id == current_user.company_id
    )
    if farm_id:
        query = query.filter(Livestock.farm_id == farm_id)
    return query.all()

@router.put("/livestock/{livestock_id}")
async def update_livestock(
    livestock_id: str,
    livestock_update: schemas.LivestockCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    livestock = db.query(Livestock).filter(
        Livestock.id == livestock_id,
        Livestock.company_id == current_user.company_id
    ).first()
    if not livestock:
        raise HTTPException(status_code=404, detail="Livestock not found")
    
    for key, value in livestock_update.dict().items():
        setattr(livestock, key, value)
    
    db.commit()
    db.refresh(livestock)
    return livestock

@router.delete("/livestock/{livestock_id}")
async def delete_livestock(
    livestock_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    livestock = db.query(Livestock).filter(
        Livestock.id == livestock_id,
        Livestock.company_id == current_user.company_id
    ).first()
    if not livestock:
        raise HTTPException(status_code=404, detail="Livestock not found")
    
    db.delete(livestock)
    db.commit()
    return {"message": "Livestock deleted successfully"}

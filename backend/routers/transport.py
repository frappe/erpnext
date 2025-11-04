from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Vehicle, Trip
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/transport", tags=["transport"])

# Vehicles
@router.post("/vehicles")
async def create_vehicle(
    vehicle: schemas.VehicleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_vehicle = Vehicle(**vehicle.dict(), company_id=current_user.company_id)
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle

@router.get("/vehicles")
async def get_vehicles(
    status: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Vehicle).filter(Vehicle.company_id == current_user.company_id)
    if status:
        query = query.filter(Vehicle.status == status)
    return query.all()

@router.put("/vehicles/{vehicle_id}")
async def update_vehicle(
    vehicle_id: str,
    vehicle_update: schemas.VehicleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id,
        Vehicle.company_id == current_user.company_id
    ).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    for key, value in vehicle_update.dict().items():
        setattr(vehicle, key, value)
    
    db.commit()
    db.refresh(vehicle)
    return vehicle

@router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id,
        Vehicle.company_id == current_user.company_id
    ).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    db.delete(vehicle)
    db.commit()
    return {"message": "Vehicle deleted successfully"}

# Trips
@router.post("/trips")
async def create_trip(
    trip: schemas.TripCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_trip = Trip(**trip.dict(), company_id=current_user.company_id)
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return db_trip

@router.get("/trips")
async def get_trips(
    vehicle_id: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Trip).filter(Trip.company_id == current_user.company_id)
    if vehicle_id:
        query = query.filter(Trip.vehicle_id == vehicle_id)
    if status:
        query = query.filter(Trip.status == status)
    return query.all()

@router.put("/trips/{trip_id}")
async def update_trip(
    trip_id: str,
    trip_update: schemas.TripCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.company_id == current_user.company_id
    ).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    for key, value in trip_update.dict().items():
        setattr(trip, key, value)
    
    db.commit()
    db.refresh(trip)
    return trip

@router.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.company_id == current_user.company_id
    ).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    db.delete(trip)
    db.commit()
    return {"message": "Trip deleted successfully"}

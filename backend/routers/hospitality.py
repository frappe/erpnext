from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Room, Reservation
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/hospitality", tags=["hospitality"])

# Rooms
@router.post("/rooms")
async def create_room(
    room: schemas.RoomCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_room = Room(**room.dict(), company_id=current_user.company_id)
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@router.get("/rooms")
async def get_rooms(
    status: str = None,
    room_type: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Room).filter(Room.company_id == current_user.company_id)
    if status:
        query = query.filter(Room.status == status)
    if room_type:
        query = query.filter(Room.room_type == room_type)
    return query.all()

@router.put("/rooms/{room_id}")
async def update_room(
    room_id: str,
    room_update: schemas.RoomCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    room = db.query(Room).filter(
        Room.id == room_id,
        Room.company_id == current_user.company_id
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    for key, value in room_update.dict().items():
        setattr(room, key, value)
    
    db.commit()
    db.refresh(room)
    return room

@router.delete("/rooms/{room_id}")
async def delete_room(
    room_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    room = db.query(Room).filter(
        Room.id == room_id,
        Room.company_id == current_user.company_id
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    db.delete(room)
    db.commit()
    return {"message": "Room deleted successfully"}

# Reservations
@router.post("/reservations")
async def create_reservation(
    reservation: schemas.ReservationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_reservation = Reservation(**reservation.dict(), company_id=current_user.company_id)
    db.add(db_reservation)
    db.commit()
    db.refresh(db_reservation)
    return db_reservation

@router.get("/reservations")
async def get_reservations(
    room_id: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Reservation).filter(Reservation.company_id == current_user.company_id)
    if room_id:
        query = query.filter(Reservation.room_id == room_id)
    if status:
        query = query.filter(Reservation.status == status)
    return query.all()

@router.put("/reservations/{reservation_id}")
async def update_reservation(
    reservation_id: str,
    reservation_update: schemas.ReservationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id,
        Reservation.company_id == current_user.company_id
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    for key, value in reservation_update.dict().items():
        setattr(reservation, key, value)
    
    db.commit()
    db.refresh(reservation)
    return reservation

@router.delete("/reservations/{reservation_id}")
async def delete_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id,
        Reservation.company_id == current_user.company_id
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    db.delete(reservation)
    db.commit()
    return {"message": "Reservation deleted successfully"}

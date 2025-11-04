from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Patient, Appointment
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/healthcare", tags=["healthcare"])

# Patients
@router.post("/patients")
async def create_patient(
    patient: schemas.PatientCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_patient = Patient(**patient.dict(), company_id=current_user.company_id)
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

@router.get("/patients")
async def get_patients(
    search: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Patient).filter(Patient.company_id == current_user.company_id)
    if search:
        query = query.filter(
            (Patient.first_name.ilike(f"%{search}%")) |
            (Patient.last_name.ilike(f"%{search}%")) |
            (Patient.patient_number.ilike(f"%{search}%"))
        )
    return query.all()

@router.get("/patients/{patient_id}")
async def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.company_id == current_user.company_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@router.put("/patients/{patient_id}")
async def update_patient(
    patient_id: str,
    patient_update: schemas.PatientCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.company_id == current_user.company_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    for key, value in patient_update.dict().items():
        setattr(patient, key, value)
    
    db.commit()
    db.refresh(patient)
    return patient

@router.delete("/patients/{patient_id}")
async def delete_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.company_id == current_user.company_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db.delete(patient)
    db.commit()
    return {"message": "Patient deleted successfully"}

# Appointments
@router.post("/appointments")
async def create_appointment(
    appointment: schemas.AppointmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_appointment = Appointment(**appointment.dict(), company_id=current_user.company_id)
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

@router.get("/appointments")
async def get_appointments(
    patient_id: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Appointment).filter(
        Appointment.company_id == current_user.company_id
    )
    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)
    if status:
        query = query.filter(Appointment.status == status)
    return query.all()

@router.put("/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    appointment_update: schemas.AppointmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.company_id == current_user.company_id
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    for key, value in appointment_update.dict().items():
        setattr(appointment, key, value)
    
    db.commit()
    db.refresh(appointment)
    return appointment

@router.delete("/appointments/{appointment_id}")
async def delete_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.company_id == current_user.company_id
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    db.delete(appointment)
    db.commit()
    return {"message": "Appointment deleted successfully"}

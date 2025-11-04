from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Student
import schemas
from auth import get_current_user

router = APIRouter(prefix="/api/education", tags=["education"])

@router.post("/students")
async def create_student(
    student: StudentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_student = Student(**student.dict(), company_id=current_user.company_id)
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@router.get("/students")
async def get_students(
    grade_level: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = db.query(Student).filter(Student.company_id == current_user.company_id)
    if grade_level:
        query = query.filter(Student.grade_level == grade_level)
    if status:
        query = query.filter(Student.status == status)
    return query.all()

@router.get("/students/{student_id}")
async def get_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.company_id == current_user.company_id
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@router.put("/students/{student_id}")
async def update_student(
    student_id: str,
    student_update: StudentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.company_id == current_user.company_id
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    for key, value in student_update.dict().items():
        setattr(student, key, value)
    
    db.commit()
    db.refresh(student)
    return student

@router.delete("/students/{student_id}")
async def delete_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.company_id == current_user.company_id
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    db.delete(student)
    db.commit()
    return {"message": "Student deleted successfully"}

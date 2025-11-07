"""
Attendance Management API Routes

Endpoints for:
- Shift definitions and management
- Employee rostering
- Attendance recording (manual, clock in/out)
- Attendance import from CSV
- Attendance reports and summaries
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, time
from pydantic import BaseModel

import models
from database import get_db
from auth import get_current_user
from services.hr.attendance_service import AttendanceService

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ShiftDefinitionCreate(BaseModel):
    shift_name: str
    shift_code: str
    start_time: str  # Format: "HH:MM"
    end_time: str    # Format: "HH:MM"
    break_duration_minutes: int = 0
    is_overnight: bool = False
    working_hours: float = 8.0
    overtime_eligible: bool = True
    description: Optional[str] = None


class ShiftAssignment(BaseModel):
    employee_id: str
    shift_id: str
    effective_date: date
    end_date: Optional[date] = None


class AttendanceRecord(BaseModel):
    employee_id: str
    attendance_date: date
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    status: str = "present"  # present, absent, leave, sick, half_day
    notes: Optional[str] = None


# ============================================================================
# SHIFT MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/shifts")
def create_shift(
    data: ShiftDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new shift definition"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = AttendanceService(db)
    
    try:
        # Parse time strings
        start_time_obj = datetime.strptime(data.start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(data.end_time, "%H:%M").time()
        
        result = service.create_shift_definition(
            company_id=current_user.company_id,
            shift_name=data.shift_name,
            shift_code=data.shift_code,
            start_time=start_time_obj,
            end_time=end_time_obj,
            break_duration_minutes=data.break_duration_minutes,
            is_overnight=data.is_overnight,
            working_hours=data.working_hours,
            overtime_eligible=data.overtime_eligible,
            description=data.description
        )
        
        return {
            "success": True,
            "message": "Shift created successfully",
            "shift": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shifts")
def list_shifts(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all shift definitions"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = AttendanceService(db)
    shifts = service.list_shift_definitions(
        company_id=current_user.company_id,
        active_only=active_only
    )
    
    return {
        "success": True,
        "shifts": shifts,
        "count": len(shifts)
    }


# ============================================================================
# EMPLOYEE ROSTERING ENDPOINTS
# ============================================================================

@router.post("/roster/assign")
def assign_shift_to_employee(
    data: ShiftAssignment,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Assign a shift to an employee"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = AttendanceService(db)
    
    try:
        result = service.assign_shift_to_employee(
            company_id=current_user.company_id,
            employee_id=data.employee_id,
            shift_id=data.shift_id,
            effective_date=data.effective_date,
            end_date=data.end_date
        )
        
        return {
            "success": True,
            "message": "Shift assigned successfully",
            "assignment": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roster/{employee_id}")
def get_employee_roster(
    employee_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get roster for an employee"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = AttendanceService(db)
    roster = service.get_employee_roster(
        company_id=current_user.company_id,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return {
        "success": True,
        "employee_id": employee_id,
        "roster": roster,
        "count": len(roster)
    }


# ============================================================================
# ATTENDANCE RECORDING ENDPOINTS
# ============================================================================

@router.post("/record")
def record_attendance(
    data: AttendanceRecord,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Record employee attendance"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = AttendanceService(db)
    
    try:
        result = service.record_attendance(
            company_id=current_user.company_id,
            employee_id=data.employee_id,
            attendance_date=data.attendance_date,
            clock_in=data.clock_in,
            clock_out=data.clock_out,
            status=data.status,
            notes=data.notes,
            recorded_by=current_user.id
        )
        
        return {
            "success": True,
            "message": "Attendance recorded successfully",
            "attendance": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records")
def get_attendance_records(
    employee_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get attendance records with filters"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = AttendanceService(db)
    records = service.get_attendance_records(
        company_id=current_user.company_id,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        status=status
    )
    
    return {
        "success": True,
        "records": records,
        "count": len(records)
    }


# ============================================================================
# ATTENDANCE IMPORT ENDPOINT
# ============================================================================

@router.post("/import")
async def import_attendance(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Import attendance records from CSV file"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV format")
    
    service = AttendanceService(db)
    
    try:
        # Read CSV content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        result = service.import_attendance_csv(
            company_id=current_user.company_id,
            csv_content=csv_content,
            recorded_by=current_user.id
        )
        
        return {
            "success": result["success"],
            "message": f"Imported {result['imported']} records with {result['errors']} errors",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ATTENDANCE SUMMARY ENDPOINT
# ============================================================================

@router.get("/summary/{employee_id}")
def get_attendance_summary(
    employee_id: str,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get attendance summary for an employee"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = AttendanceService(db)
    
    try:
        summary = service.get_attendance_summary(
            company_id=current_user.company_id,
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "summary": summary
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CLOCK IN/OUT ENDPOINTS (Self-Service)
# ============================================================================

@router.post("/clock-in")
def clock_in(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Employee clock-in (self-service)"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Find employee record for current user
    employee = db.query(models.Employee).filter(
        models.Employee.company_id == current_user.company_id,
        models.Employee.email == current_user.email
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee record not found for current user"
        )
    
    service = AttendanceService(db)
    
    try:
        result = service.record_attendance(
            company_id=current_user.company_id,
            employee_id=employee.id,
            attendance_date=date.today(),
            clock_in=datetime.now(),
            status="present",
            recorded_by=current_user.id
        )
        
        return {
            "success": True,
            "message": "Clocked in successfully",
            "attendance": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clock-out")
def clock_out(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Employee clock-out (self-service)"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Find employee record for current user
    employee = db.query(models.Employee).filter(
        models.Employee.company_id == current_user.company_id,
        models.Employee.email == current_user.email
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee record not found for current user"
        )
    
    service = AttendanceService(db)
    
    try:
        result = service.record_attendance(
            company_id=current_user.company_id,
            employee_id=employee.id,
            attendance_date=date.today(),
            clock_out=datetime.now(),
            status="present",
            recorded_by=current_user.id
        )
        
        return {
            "success": True,
            "message": "Clocked out successfully",
            "attendance": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

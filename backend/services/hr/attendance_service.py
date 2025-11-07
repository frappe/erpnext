"""
Attendance Management Service

Handles:
- Shift definitions and templates
- Employee rostering
- Attendance capture (clock in/out, manual entry, import)
- Overtime calculations
- Integration with payroll
"""

from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException
import models
import csv
from io import StringIO


class AttendanceService:
    """Manages employee attendance, shifts, and rostering"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # SHIFT MANAGEMENT
    # ========================================================================
    
    def create_shift_definition(
        self,
        company_id: str,
        shift_name: str,
        shift_code: str,
        start_time: time,
        end_time: time,
        break_duration_minutes: int = 0,
        is_overnight: bool = False,
        working_hours: float = 8.0,
        overtime_eligible: bool = True,
        description: Optional[str] = None
    ) -> Dict:
        """Create a shift definition template"""
        
        # Check for duplicate shift code
        existing = self.db.query(models.ShiftDefinition).filter(
            models.ShiftDefinition.company_id == company_id,
            models.ShiftDefinition.shift_code == shift_code
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Shift code already exists")
        
        shift = models.ShiftDefinition(
            company_id=company_id,
            shift_name=shift_name,
            shift_code=shift_code,
            start_time=start_time,
            end_time=end_time,
            break_duration_minutes=break_duration_minutes,
            is_overnight=is_overnight,
            working_hours=working_hours,
            overtime_eligible=overtime_eligible,
            description=description,
            is_active=True
        )
        
        self.db.add(shift)
        self.db.commit()
        self.db.refresh(shift)
        
        return self._shift_to_dict(shift)
    
    def list_shift_definitions(self, company_id: str, active_only: bool = True) -> List[Dict]:
        """List all shift definitions for a company"""
        query = self.db.query(models.ShiftDefinition).filter(
            models.ShiftDefinition.company_id == company_id
        )
        
        if active_only:
            query = query.filter(models.ShiftDefinition.is_active == True)
        
        shifts = query.order_by(models.ShiftDefinition.shift_code).all()
        return [self._shift_to_dict(shift) for shift in shifts]
    
    def _shift_to_dict(self, shift: models.ShiftDefinition) -> Dict:
        """Convert shift definition to dictionary"""
        return {
            "id": shift.id,
            "shift_name": shift.shift_name,
            "shift_code": shift.shift_code,
            "start_time": shift.start_time.strftime("%H:%M") if shift.start_time else None,
            "end_time": shift.end_time.strftime("%H:%M") if shift.end_time else None,
            "break_duration_minutes": shift.break_duration_minutes,
            "is_overnight": shift.is_overnight,
            "working_hours": shift.working_hours,
            "overtime_eligible": shift.overtime_eligible,
            "description": shift.description,
            "is_active": shift.is_active
        }
    
    # ========================================================================
    # EMPLOYEE ROSTERING
    # ========================================================================
    
    def assign_shift_to_employee(
        self,
        company_id: str,
        employee_id: str,
        shift_id: str,
        effective_date: date,
        end_date: Optional[date] = None
    ) -> Dict:
        """Assign a shift to an employee"""
        
        # Validate employee
        employee = self.db.query(models.Employee).filter(
            models.Employee.id == employee_id,
            models.Employee.company_id == company_id
        ).first()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Validate shift
        shift = self.db.query(models.ShiftDefinition).filter(
            models.ShiftDefinition.id == shift_id,
            models.ShiftDefinition.company_id == company_id
        ).first()
        
        if not shift:
            raise HTTPException(status_code=404, detail="Shift not found")
        
        # Create roster assignment
        roster = models.EmployeeShiftRoster(
            company_id=company_id,
            employee_id=employee_id,
            shift_id=shift_id,
            effective_date=effective_date,
            end_date=end_date,
            is_active=True
        )
        
        self.db.add(roster)
        self.db.commit()
        self.db.refresh(roster)
        
        return {
            "id": roster.id,
            "employee_id": employee_id,
            "employee_name": f"{employee.first_name} {employee.last_name}",
            "shift_id": shift_id,
            "shift_name": shift.shift_name,
            "effective_date": effective_date.isoformat(),
            "end_date": end_date.isoformat() if end_date else None
        }
    
    def get_employee_roster(
        self,
        company_id: str,
        employee_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """Get roster for an employee"""
        query = self.db.query(models.EmployeeShiftRoster).filter(
            models.EmployeeShiftRoster.company_id == company_id,
            models.EmployeeShiftRoster.employee_id == employee_id,
            models.EmployeeShiftRoster.is_active == True
        )
        
        if start_date:
            query = query.filter(
                or_(
                    models.EmployeeShiftRoster.end_date == None,
                    models.EmployeeShiftRoster.end_date >= start_date
                )
            )
        
        if end_date:
            query = query.filter(models.EmployeeShiftRoster.effective_date <= end_date)
        
        rosters = query.all()
        
        result = []
        for roster in rosters:
            shift = self.db.query(models.ShiftDefinition).filter(
                models.ShiftDefinition.id == roster.shift_id
            ).first()
            
            result.append({
                "id": roster.id,
                "shift_id": roster.shift_id,
                "shift_name": shift.shift_name if shift else "Unknown",
                "shift_code": shift.shift_code if shift else "N/A",
                "effective_date": roster.effective_date.isoformat(),
                "end_date": roster.end_date.isoformat() if roster.end_date else None,
                "start_time": shift.start_time.strftime("%H:%M") if shift and shift.start_time else None,
                "end_time": shift.end_time.strftime("%H:%M") if shift and shift.end_time else None
            })
        
        return result
    
    # ========================================================================
    # ATTENDANCE CAPTURE
    # ========================================================================
    
    def record_attendance(
        self,
        company_id: str,
        employee_id: str,
        attendance_date: date,
        clock_in: Optional[datetime] = None,
        clock_out: Optional[datetime] = None,
        status: str = "present",
        notes: Optional[str] = None,
        recorded_by: Optional[str] = None
    ) -> Dict:
        """Record employee attendance"""
        
        # Validate employee
        employee = self.db.query(models.Employee).filter(
            models.Employee.id == employee_id,
            models.Employee.company_id == company_id
        ).first()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Check for existing attendance
        existing = self.db.query(models.AttendanceRecord).filter(
            models.AttendanceRecord.company_id == company_id,
            models.AttendanceRecord.employee_id == employee_id,
            models.AttendanceRecord.attendance_date == attendance_date
        ).first()
        
        if existing:
            # Update existing record
            if clock_in:
                existing.clock_in = clock_in
            if clock_out:
                existing.clock_out = clock_out
            existing.status = status
            if notes:
                existing.notes = notes
            
            self.db.commit()
            self.db.refresh(existing)
            return self._attendance_to_dict(existing, employee)
        
        # Calculate hours worked
        hours_worked = None
        if clock_in and clock_out:
            hours_worked = (clock_out - clock_in).total_seconds() / 3600
        
        # Create new attendance record
        attendance = models.AttendanceRecord(
            company_id=company_id,
            employee_id=employee_id,
            attendance_date=attendance_date,
            clock_in=clock_in,
            clock_out=clock_out,
            hours_worked=hours_worked,
            status=status,
            notes=notes,
            recorded_by=recorded_by
        )
        
        self.db.add(attendance)
        self.db.commit()
        self.db.refresh(attendance)
        
        return self._attendance_to_dict(attendance, employee)
    
    def get_attendance_records(
        self,
        company_id: str,
        employee_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None
    ) -> List[Dict]:
        """Get attendance records with filters"""
        query = self.db.query(models.AttendanceRecord).filter(
            models.AttendanceRecord.company_id == company_id
        )
        
        if employee_id:
            query = query.filter(models.AttendanceRecord.employee_id == employee_id)
        
        if start_date:
            query = query.filter(models.AttendanceRecord.attendance_date >= start_date)
        
        if end_date:
            query = query.filter(models.AttendanceRecord.attendance_date <= end_date)
        
        if status:
            query = query.filter(models.AttendanceRecord.status == status)
        
        records = query.order_by(
            models.AttendanceRecord.attendance_date.desc(),
            models.AttendanceRecord.clock_in.desc()
        ).all()
        
        result = []
        for record in records:
            employee = self.db.query(models.Employee).filter(
                models.Employee.id == record.employee_id
            ).first()
            result.append(self._attendance_to_dict(record, employee))
        
        return result
    
    def _attendance_to_dict(self, attendance: models.AttendanceRecord, employee: Optional[models.Employee] = None) -> Dict:
        """Convert attendance record to dictionary"""
        return {
            "id": attendance.id,
            "employee_id": attendance.employee_id,
            "employee_name": f"{employee.first_name} {employee.last_name}" if employee else "Unknown",
            "employee_no": employee.employee_no if employee else "N/A",
            "attendance_date": attendance.attendance_date.isoformat(),
            "clock_in": attendance.clock_in.isoformat() if attendance.clock_in else None,
            "clock_out": attendance.clock_out.isoformat() if attendance.clock_out else None,
            "hours_worked": attendance.hours_worked,
            "overtime_hours": attendance.overtime_hours,
            "status": attendance.status,
            "notes": attendance.notes,
            "recorded_by": attendance.recorded_by
        }
    
    # ========================================================================
    # ATTENDANCE IMPORT
    # ========================================================================
    
    def import_attendance_csv(
        self,
        company_id: str,
        csv_content: str,
        recorded_by: str
    ) -> Dict:
        """
        Import attendance from CSV
        
        Expected format:
        employee_no,date,clock_in,clock_out,status,notes
        """
        csv_file = StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        success_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):
            try:
                # Get employee by employee number
                employee = self.db.query(models.Employee).filter(
                    models.Employee.company_id == company_id,
                    models.Employee.employee_no == row['employee_no']
                ).first()
                
                if not employee:
                    errors.append(f"Row {row_num}: Employee {row['employee_no']} not found")
                    error_count += 1
                    continue
                
                # Parse date and times
                attendance_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                clock_in = datetime.strptime(row['clock_in'], '%Y-%m-%d %H:%M') if row.get('clock_in') else None
                clock_out = datetime.strptime(row['clock_out'], '%Y-%m-%d %H:%M') if row.get('clock_out') else None
                
                # Record attendance
                self.record_attendance(
                    company_id=company_id,
                    employee_id=employee.id,
                    attendance_date=attendance_date,
                    clock_in=clock_in,
                    clock_out=clock_out,
                    status=row.get('status', 'present'),
                    notes=row.get('notes'),
                    recorded_by=recorded_by
                )
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                error_count += 1
        
        return {
            "success": error_count == 0,
            "imported": success_count,
            "errors": error_count,
            "error_details": errors if errors else None
        }
    
    # ========================================================================
    # ATTENDANCE SUMMARY
    # ========================================================================
    
    def get_attendance_summary(
        self,
        company_id: str,
        employee_id: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Get attendance summary for an employee over a period"""
        records = self.get_attendance_records(
            company_id=company_id,
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date
        )
        
        total_days = (end_date - start_date).days + 1
        present_days = sum(1 for r in records if r['status'] == 'present')
        absent_days = sum(1 for r in records if r['status'] == 'absent')
        leave_days = sum(1 for r in records if r['status'] == 'leave')
        total_hours = sum(r['hours_worked'] or 0 for r in records)
        total_overtime = sum(r['overtime_hours'] or 0 for r in records)
        
        return {
            "employee_id": employee_id,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_days": total_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "leave_days": leave_days,
            "total_hours_worked": round(total_hours, 2),
            "total_overtime_hours": round(total_overtime, 2),
            "attendance_rate": round((present_days / total_days * 100), 2) if total_days > 0 else 0
        }

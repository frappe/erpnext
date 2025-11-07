"""
Leave Management Service

Handles:
- Leave type configuration
- Leave request submission
- Approval workflow (multi-level)
- Leave balance tracking
- Integration with payroll and attendance
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException
import models


class LeaveService:
    """Manages employee leave requests and approvals"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # LEAVE TYPE MANAGEMENT
    # ========================================================================
    
    def create_leave_type(
        self,
        company_id: str,
        leave_type_code: str,
        leave_type_name: str,
        annual_entitlement: float,
        is_paid: bool = True,
        requires_approval: bool = True,
        max_consecutive_days: Optional[int] = None,
        min_notice_days: int = 0,
        description: Optional[str] = None
    ) -> Dict:
        """Create a leave type configuration"""
        
        # Check for duplicate code
        existing = self.db.query(models.LeaveTypeConfiguration).filter(
            models.LeaveTypeConfiguration.company_id == company_id,
            models.LeaveTypeConfiguration.leave_type_code == leave_type_code
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Leave type code already exists")
        
        leave_type = models.LeaveTypeConfiguration(
            company_id=company_id,
            leave_type_code=leave_type_code,
            leave_type_name=leave_type_name,
            annual_entitlement=annual_entitlement,
            is_paid=is_paid,
            requires_approval=requires_approval,
            max_consecutive_days=max_consecutive_days,
            min_notice_days=min_notice_days,
            description=description,
            is_active=True
        )
        
        self.db.add(leave_type)
        self.db.commit()
        self.db.refresh(leave_type)
        
        return self._leave_type_to_dict(leave_type)
    
    def list_leave_types(self, company_id: str, active_only: bool = True) -> List[Dict]:
        """List all leave types for a company"""
        query = self.db.query(models.LeaveTypeConfiguration).filter(
            models.LeaveTypeConfiguration.company_id == company_id
        )
        
        if active_only:
            query = query.filter(models.LeaveTypeConfiguration.is_active == True)
        
        leave_types = query.order_by(models.LeaveTypeConfiguration.leave_type_code).all()
        return [self._leave_type_to_dict(lt) for lt in leave_types]
    
    def _leave_type_to_dict(self, leave_type: models.LeaveTypeConfiguration) -> Dict:
        """Convert leave type to dictionary"""
        return {
            "id": leave_type.id,
            "leave_type_code": leave_type.leave_type_code,
            "leave_type_name": leave_type.leave_type_name,
            "annual_entitlement": leave_type.annual_entitlement,
            "is_paid": leave_type.is_paid,
            "requires_approval": leave_type.requires_approval,
            "max_consecutive_days": leave_type.max_consecutive_days,
            "min_notice_days": leave_type.min_notice_days,
            "description": leave_type.description,
            "is_active": leave_type.is_active
        }
    
    # ========================================================================
    # LEAVE BALANCE MANAGEMENT
    # ========================================================================
    
    def initialize_employee_leave_balances(
        self,
        company_id: str,
        employee_id: str,
        year: int
    ) -> List[Dict]:
        """Initialize leave balances for an employee for a year"""
        
        # Get all active leave types
        leave_types = self.list_leave_types(company_id, active_only=True)
        
        balances = []
        for leave_type in leave_types:
            # Check if balance already exists
            existing = self.db.query(models.EmployeeLeaveBalance).filter(
                models.EmployeeLeaveBalance.company_id == company_id,
                models.EmployeeLeaveBalance.employee_id == employee_id,
                models.EmployeeLeaveBalance.leave_type_id == leave_type['id'],
                models.EmployeeLeaveBalance.year == year
            ).first()
            
            if existing:
                continue
            
            # Create new balance
            balance = models.EmployeeLeaveBalance(
                company_id=company_id,
                employee_id=employee_id,
                leave_type_id=leave_type['id'],
                year=year,
                entitled_days=leave_type['annual_entitlement'],
                accrued_days=leave_type['annual_entitlement'],
                taken_days=0.0,
                pending_days=0.0,
                balance_days=leave_type['annual_entitlement']
            )
            
            self.db.add(balance)
            balances.append(balance)
        
        self.db.commit()
        
        return [self._balance_to_dict(b) for b in balances]
    
    def get_leave_balance(
        self,
        company_id: str,
        employee_id: str,
        leave_type_id: str,
        year: int
    ) -> Optional[Dict]:
        """Get leave balance for an employee"""
        balance = self.db.query(models.EmployeeLeaveBalance).filter(
            models.EmployeeLeaveBalance.company_id == company_id,
            models.EmployeeLeaveBalance.employee_id == employee_id,
            models.EmployeeLeaveBalance.leave_type_id == leave_type_id,
            models.EmployeeLeaveBalance.year == year
        ).first()
        
        if not balance:
            return None
        
        return self._balance_to_dict(balance)
    
    def get_all_leave_balances(
        self,
        company_id: str,
        employee_id: str,
        year: int
    ) -> List[Dict]:
        """Get all leave balances for an employee"""
        balances = self.db.query(models.EmployeeLeaveBalance).filter(
            models.EmployeeLeaveBalance.company_id == company_id,
            models.EmployeeLeaveBalance.employee_id == employee_id,
            models.EmployeeLeaveBalance.year == year
        ).all()
        
        result = []
        for balance in balances:
            # Get leave type details
            leave_type = self.db.query(models.LeaveTypeConfiguration).filter(
                models.LeaveTypeConfiguration.id == balance.leave_type_id
            ).first()
            
            balance_dict = self._balance_to_dict(balance)
            if leave_type:
                balance_dict['leave_type_name'] = leave_type.leave_type_name
                balance_dict['leave_type_code'] = leave_type.leave_type_code
            
            result.append(balance_dict)
        
        return result
    
    def _balance_to_dict(self, balance: models.EmployeeLeaveBalance) -> Dict:
        """Convert leave balance to dictionary"""
        return {
            "id": balance.id,
            "employee_id": balance.employee_id,
            "leave_type_id": balance.leave_type_id,
            "year": balance.year,
            "entitled_days": balance.entitled_days,
            "accrued_days": balance.accrued_days,
            "taken_days": balance.taken_days,
            "pending_days": balance.pending_days,
            "balance_days": balance.balance_days
        }
    
    # ========================================================================
    # LEAVE REQUEST MANAGEMENT
    # ========================================================================
    
    def submit_leave_request(
        self,
        company_id: str,
        employee_id: str,
        leave_type_id: str,
        start_date: date,
        end_date: date,
        reason: str,
        submitted_by: str,
        days_requested: Optional[float] = None
    ) -> Dict:
        """Submit a leave request"""
        
        # Validate employee
        employee = self.db.query(models.Employee).filter(
            models.Employee.id == employee_id,
            models.Employee.company_id == company_id
        ).first()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Validate leave type
        leave_type = self.db.query(models.LeaveTypeConfiguration).filter(
            models.LeaveTypeConfiguration.id == leave_type_id,
            models.LeaveTypeConfiguration.company_id == company_id
        ).first()
        
        if not leave_type:
            raise HTTPException(status_code=404, detail="Leave type not found")
        
        # Calculate days if not provided
        if days_requested is None:
            days_requested = (end_date - start_date).days + 1
        
        # Check minimum notice
        notice_days = (start_date - date.today()).days
        if notice_days < leave_type.min_notice_days:
            raise HTTPException(
                status_code=400,
                detail=f"Minimum notice of {leave_type.min_notice_days} days required"
            )
        
        # Check maximum consecutive days
        if leave_type.max_consecutive_days and days_requested > leave_type.max_consecutive_days:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum consecutive days is {leave_type.max_consecutive_days}"
            )
        
        # Check leave balance
        year = start_date.year
        balance = self.get_leave_balance(company_id, employee_id, leave_type_id, year)
        
        if not balance:
            # Initialize balance if not exists
            self.initialize_employee_leave_balances(company_id, employee_id, year)
            balance = self.get_leave_balance(company_id, employee_id, leave_type_id, year)
        
        if balance and balance['balance_days'] < days_requested:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient leave balance. Available: {balance['balance_days']} days"
            )
        
        # Create leave request
        leave_request = models.LeaveRequest(
            company_id=company_id,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            days_requested=days_requested,
            reason=reason,
            status="pending",
            submitted_by=submitted_by,
            submitted_at=datetime.utcnow()
        )
        
        self.db.add(leave_request)
        
        # Update pending days in balance
        if balance:
            balance_record = self.db.query(models.EmployeeLeaveBalance).filter(
                models.EmployeeLeaveBalance.id == balance['id']
            ).first()
            if balance_record:
                balance_record.pending_days += days_requested
                balance_record.balance_days = balance_record.accrued_days - balance_record.taken_days - balance_record.pending_days
        
        self.db.commit()
        self.db.refresh(leave_request)
        
        return self._leave_request_to_dict(leave_request, employee, leave_type)
    
    def approve_leave_request(
        self,
        company_id: str,
        leave_request_id: str,
        approved_by: str,
        comments: Optional[str] = None
    ) -> Dict:
        """Approve a leave request"""
        
        leave_request = self.db.query(models.LeaveRequest).filter(
            models.LeaveRequest.id == leave_request_id,
            models.LeaveRequest.company_id == company_id
        ).first()
        
        if not leave_request:
            raise HTTPException(status_code=404, detail="Leave request not found")
        
        if leave_request.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve request with status: {leave_request.status}"
            )
        
        # Update request status
        leave_request.status = "approved"
        leave_request.approved_by = approved_by
        leave_request.approved_at = datetime.utcnow()
        leave_request.approver_comments = comments
        
        # Update leave balance
        year = leave_request.start_date.year
        balance = self.db.query(models.EmployeeLeaveBalance).filter(
            models.EmployeeLeaveBalance.company_id == company_id,
            models.EmployeeLeaveBalance.employee_id == leave_request.employee_id,
            models.EmployeeLeaveBalance.leave_type_id == leave_request.leave_type_id,
            models.EmployeeLeaveBalance.year == year
        ).first()
        
        if balance:
            balance.pending_days -= leave_request.days_requested
            balance.taken_days += leave_request.days_requested
            balance.balance_days = balance.accrued_days - balance.taken_days - balance.pending_days
        
        self.db.commit()
        self.db.refresh(leave_request)
        
        employee = self.db.query(models.Employee).get(leave_request.employee_id)
        leave_type = self.db.query(models.LeaveTypeConfiguration).get(leave_request.leave_type_id)
        
        return self._leave_request_to_dict(leave_request, employee, leave_type)
    
    def reject_leave_request(
        self,
        company_id: str,
        leave_request_id: str,
        rejected_by: str,
        rejection_reason: str
    ) -> Dict:
        """Reject a leave request"""
        
        leave_request = self.db.query(models.LeaveRequest).filter(
            models.LeaveRequest.id == leave_request_id,
            models.LeaveRequest.company_id == company_id
        ).first()
        
        if not leave_request:
            raise HTTPException(status_code=404, detail="Leave request not found")
        
        if leave_request.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reject request with status: {leave_request.status}"
            )
        
        # Update request status
        leave_request.status = "rejected"
        leave_request.approved_by = rejected_by
        leave_request.approved_at = datetime.utcnow()
        leave_request.approver_comments = rejection_reason
        
        # Restore pending days in balance
        year = leave_request.start_date.year
        balance = self.db.query(models.EmployeeLeaveBalance).filter(
            models.EmployeeLeaveBalance.company_id == company_id,
            models.EmployeeLeaveBalance.employee_id == leave_request.employee_id,
            models.EmployeeLeaveBalance.leave_type_id == leave_request.leave_type_id,
            models.EmployeeLeaveBalance.year == year
        ).first()
        
        if balance:
            balance.pending_days -= leave_request.days_requested
            balance.balance_days = balance.accrued_days - balance.taken_days - balance.pending_days
        
        self.db.commit()
        self.db.refresh(leave_request)
        
        employee = self.db.query(models.Employee).get(leave_request.employee_id)
        leave_type = self.db.query(models.LeaveTypeConfiguration).get(leave_request.leave_type_id)
        
        return self._leave_request_to_dict(leave_request, employee, leave_type)
    
    def get_leave_requests(
        self,
        company_id: str,
        employee_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """Get leave requests with filters"""
        query = self.db.query(models.LeaveRequest).filter(
            models.LeaveRequest.company_id == company_id
        )
        
        if employee_id:
            query = query.filter(models.LeaveRequest.employee_id == employee_id)
        
        if status:
            query = query.filter(models.LeaveRequest.status == status)
        
        if start_date:
            query = query.filter(models.LeaveRequest.start_date >= start_date)
        
        if end_date:
            query = query.filter(models.LeaveRequest.end_date <= end_date)
        
        requests = query.order_by(models.LeaveRequest.submitted_at.desc()).all()
        
        result = []
        for request in requests:
            employee = self.db.query(models.Employee).get(request.employee_id)
            leave_type = self.db.query(models.LeaveTypeConfiguration).get(request.leave_type_id)
            result.append(self._leave_request_to_dict(request, employee, leave_type))
        
        return result
    
    def _leave_request_to_dict(
        self,
        request: models.LeaveRequest,
        employee: Optional[models.Employee] = None,
        leave_type: Optional[models.LeaveTypeConfiguration] = None
    ) -> Dict:
        """Convert leave request to dictionary"""
        return {
            "id": request.id,
            "employee_id": request.employee_id,
            "employee_name": f"{employee.first_name} {employee.last_name}" if employee else "Unknown",
            "employee_no": employee.employee_no if employee else "N/A",
            "leave_type_id": request.leave_type_id,
            "leave_type_name": leave_type.leave_type_name if leave_type else "Unknown",
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "days_requested": request.days_requested,
            "reason": request.reason,
            "status": request.status,
            "submitted_by": request.submitted_by,
            "submitted_at": request.submitted_at.isoformat() if request.submitted_at else None,
            "approved_by": request.approved_by,
            "approved_at": request.approved_at.isoformat() if request.approved_at else None,
            "approver_comments": request.approver_comments
        }

"""
TPIN Validation Service

Handles validation of Zambian Tax Personal Identification Numbers (TPIN).
TPINs are issued by Zambia Revenue Authority (ZRA) for tax purposes.

TPIN Format: 10 digits (e.g., 1234567890)
"""

from datetime import datetime, date
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException
import models
import re


class TPINValidationService:
    """Validates and tracks TPIN validation status"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # TPIN VALIDATION
    # ========================================================================
    
    def validate_tpin_format(self, tpin: str) -> Dict:
        """
        Validate TPIN format (basic validation)
        
        TPIN Rules:
        - Must be exactly 10 digits
        - No letters or special characters
        - Cannot start with 0
        """
        
        # Remove any whitespace
        tpin = tpin.strip()
        
        # Check length
        if len(tpin) != 10:
            return {
                "valid": False,
                "error": "TPIN must be exactly 10 digits",
                "tpin": tpin
            }
        
        # Check if all digits
        if not tpin.isdigit():
            return {
                "valid": False,
                "error": "TPIN must contain only digits",
                "tpin": tpin
            }
        
        # Check if starts with 0
        if tpin[0] == '0':
            return {
                "valid": False,
                "error": "TPIN cannot start with 0",
                "tpin": tpin
            }
        
        return {
            "valid": True,
            "tpin": tpin,
            "formatted": f"{tpin[:4]} {tpin[4:7]} {tpin[7:]}"
        }
    
    def validate_tpin_with_zra(self, tpin: str, employee_name: str) -> Dict:
        """
        Validate TPIN with ZRA (mock implementation)
        
        In production, this would call ZRA API:
        - Verify TPIN exists in ZRA system
        - Confirm name matches
        - Check registration status
        - Get taxpayer details
        
        For now, implements mock validation logic.
        """
        
        # First, validate format
        format_check = self.validate_tpin_format(tpin)
        if not format_check["valid"]:
            return format_check
        
        # Mock ZRA API call
        # In production: api_response = zra_api.verify_tpin(tpin, employee_name)
        
        # Mock logic: TPINs ending in 00-09 are "invalid", others are "valid"
        last_two = tpin[-2:]
        
        if last_two in ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09']:
            return {
                "valid": False,
                "verified": False,
                "tpin": tpin,
                "error": "TPIN not found in ZRA database (mock validation)",
                "validation_date": datetime.now().isoformat(),
                "validation_method": "mock_zra_api"
            }
        
        # Mock successful validation
        return {
            "valid": True,
            "verified": True,
            "tpin": tpin,
            "formatted": format_check["formatted"],
            "taxpayer_name": employee_name,
            "registration_status": "active",
            "registration_date": "2020-01-01",
            "tax_office": "Lusaka Tax District",
            "validation_date": datetime.now().isoformat(),
            "validation_method": "mock_zra_api",
            "note": "This is a mock validation. In production, this would call the actual ZRA API."
        }
    
    def update_employee_tpin_status(
        self,
        company_id: str,
        employee_id: str,
        tpin: str,
        validate_with_zra: bool = False
    ) -> Dict:
        """Update employee TPIN and validation status"""
        
        # Get employee
        employee = self.db.query(models.Employee).filter(
            models.Employee.id == employee_id,
            models.Employee.company_id == company_id
        ).first()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Validate TPIN
        if validate_with_zra:
            employee_name = f"{employee.first_name} {employee.last_name}"
            validation_result = self.validate_tpin_with_zra(tpin, employee_name)
        else:
            validation_result = self.validate_tpin_format(tpin)
        
        if not validation_result["valid"]:
            return {
                "success": False,
                "employee_id": employee_id,
                "validation_result": validation_result
            }
        
        # Update employee TPIN
        employee.tpin = tpin
        employee.tpin_verified = validation_result.get("verified", False)
        
        self.db.commit()
        self.db.refresh(employee)
        
        return {
            "success": True,
            "employee_id": employee_id,
            "employee_name": f"{employee.first_name} {employee.last_name}",
            "tpin": tpin,
            "validation_result": validation_result
        }
    
    # ========================================================================
    # BULK VALIDATION
    # ========================================================================
    
    def validate_company_tpins(
        self,
        company_id: str,
        validate_with_zra: bool = False
    ) -> Dict:
        """Validate TPINs for all employees in a company"""
        
        employees = self.db.query(models.Employee).filter(
            models.Employee.company_id == company_id,
            models.Employee.status == "active"
        ).all()
        
        results = []
        valid_count = 0
        invalid_count = 0
        missing_count = 0
        
        for employee in employees:
            if not employee.tpin:
                missing_count += 1
                results.append({
                    "employee_id": employee.id,
                    "employee_name": f"{employee.first_name} {employee.last_name}",
                    "employee_number": employee.employee_no,
                    "status": "missing",
                    "message": "TPIN not provided"
                })
                continue
            
            # Validate TPIN
            if validate_with_zra:
                employee_name = f"{employee.first_name} {employee.last_name}"
                validation = self.validate_tpin_with_zra(employee.tpin, employee_name)
            else:
                validation = self.validate_tpin_format(employee.tpin)
            
            if validation["valid"]:
                valid_count += 1
                status = "valid"
            else:
                invalid_count += 1
                status = "invalid"
            
            results.append({
                "employee_id": employee.id,
                "employee_name": f"{employee.first_name} {employee.last_name}",
                "employee_number": employee.employee_no,
                "tpin": employee.tpin,
                "status": status,
                "validation": validation
            })
        
        return {
            "success": True,
            "total_employees": len(employees),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "missing_count": missing_count,
            "results": results
        }
    
    # ========================================================================
    # TPIN REPORTS
    # ========================================================================
    
    def get_employees_without_tpin(self, company_id: str) -> Dict:
        """Get list of employees missing TPIN"""
        
        employees = self.db.query(models.Employee).filter(
            models.Employee.company_id == company_id,
            models.Employee.status == "active",
            models.Employee.tpin.is_(None)
        ).all()
        
        return {
            "success": True,
            "count": len(employees),
            "employees": [
                {
                    "id": emp.id,
                    "employee_number": emp.employee_no,
                    "name": f"{emp.first_name} {emp.last_name}",
                    "email": emp.email,
                    "department": emp.department_id,
                    "position": emp.position
                }
                for emp in employees
            ]
        }
    
    def get_employees_with_unverified_tpin(self, company_id: str) -> Dict:
        """Get list of employees with unverified TPIN"""
        
        employees = self.db.query(models.Employee).filter(
            models.Employee.company_id == company_id,
            models.Employee.status == "active",
            models.Employee.tpin.isnot(None),
            models.Employee.tpin_verified == False
        ).all()
        
        return {
            "success": True,
            "count": len(employees),
            "employees": [
                {
                    "id": emp.id,
                    "employee_number": emp.employee_no,
                    "name": f"{emp.first_name} {emp.last_name}",
                    "tpin": emp.tpin,
                    "email": emp.email,
                    "department": emp.department_id
                }
                for emp in employees
            ]
        }

"""
Compliance Validation & Statutory Exports API Router

Endpoints for:
- TPIN validation
- NAPSA exports
- NHIMA exports  
- PAYE exports
- Combined statutory reports
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

import models
from database import get_db
from auth import get_current_user
from services.compliance.tpin_validation_service import TPINValidationService
from services.compliance.statutory_export_service import StatutoryExportService

router = APIRouter(prefix="/api/compliance", tags=["Compliance & Statutory"])


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class TPINValidationRequest(BaseModel):
    tpin: str
    validate_with_zra: bool = False


class TPINUpdateRequest(BaseModel):
    employee_id: str
    tpin: str
    validate_with_zra: bool = False


# ============================================================================
# TPIN VALIDATION
# ============================================================================

@router.post("/validate-tpin")
def validate_tpin_format(
    data: TPINValidationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Validate TPIN format or with ZRA"""
    service = TPINValidationService(db)
    
    try:
        if data.validate_with_zra:
            result = service.validate_tpin_with_zra(data.tpin, "Unknown")
        else:
            result = service.validate_tpin_format(data.tpin)
        
        return {
            "success": True,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-employee-tpin")
def update_employee_tpin(
    data: TPINUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update employee TPIN and validate"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = TPINValidationService(db)
    
    try:
        result = service.update_employee_tpin_status(
            company_id=current_user.company_id,
            employee_id=data.employee_id,
            tpin=data.tpin,
            validate_with_zra=data.validate_with_zra
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-all-tpins")
def validate_company_tpins(
    validate_with_zra: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Validate TPINs for all company employees"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = TPINValidationService(db)
    
    try:
        result = service.validate_company_tpins(
            company_id=current_user.company_id,
            validate_with_zra=validate_with_zra
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees-without-tpin")
def get_employees_without_tpin(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get list of employees missing TPIN"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = TPINValidationService(db)
    
    try:
        result = service.get_employees_without_tpin(
            company_id=current_user.company_id
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees-unverified-tpin")
def get_employees_with_unverified_tpin(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get list of employees with unverified TPIN"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = TPINValidationService(db)
    
    try:
        result = service.get_employees_with_unverified_tpin(
            company_id=current_user.company_id
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATUTORY EXPORTS
# ============================================================================

@router.get("/export/napsa/{payrun_id}")
def export_napsa(
    payrun_id: str,
    format: str = "csv",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Export NAPSA contribution report"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = StatutoryExportService(db)
    
    try:
        result = service.generate_napsa_export(
            company_id=current_user.company_id,
            payrun_id=payrun_id,
            format=format
        )
        
        if format == "csv":
            return Response(
                content=result["content"],
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{result["filename"]}"'
                }
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/nhima/{payrun_id}")
def export_nhima(
    payrun_id: str,
    format: str = "csv",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Export NHIMA contribution report"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = StatutoryExportService(db)
    
    try:
        result = service.generate_nhima_export(
            company_id=current_user.company_id,
            payrun_id=payrun_id,
            format=format
        )
        
        if format == "csv":
            return Response(
                content=result["content"],
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{result["filename"]}"'
                }
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/paye/{payrun_id}")
def export_paye(
    payrun_id: str,
    format: str = "csv",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Export PAYE return for ZRA"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = StatutoryExportService(db)
    
    try:
        result = service.generate_paye_export(
            company_id=current_user.company_id,
            payrun_id=payrun_id,
            format=format
        )
        
        if format == "csv":
            return Response(
                content=result["content"],
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{result["filename"]}"'
                }
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/statutory-summary/{payrun_id}")
def export_combined_statutory_report(
    payrun_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get combined statutory report summary"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    service = StatutoryExportService(db)
    
    try:
        result = service.generate_combined_statutory_report(
            company_id=current_user.company_id,
            payrun_id=payrun_id
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
Employee Management API Routes (Enhanced with Zambian Compliance)

Endpoints for:
- Employee CRUD with full Zambian compliance fields
- Employment contracts
- Job requisitions
- Employee onboarding/offboarding
- Document management
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from pydantic import BaseModel

import models
from database import get_db
from auth import get_current_user
from services.hr.document_manager import DocumentManager

router = APIRouter(prefix="/api/employees", tags=["Employees"])


class EmployeeCreate(BaseModel):
    employee_no: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    maiden_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    
    # Personal Details
    id_number: Optional[str] = None
    passport_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: str = "Zambian"
    
    # Address
    residential_address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    
    # Employment
    position: Optional[str] = None
    department_id: Optional[str] = None
    supervisor_id: Optional[str] = None
    date_joined: Optional[date] = None
    employment_type: str = "permanent"
    salary_base: float = 0.0
    
    # Banking
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    
    # Statutory IDs
    tax_id: Optional[str] = None  # TPIN
    napsa_number: Optional[str] = None
    nhima_number: Optional[str] = None
    workers_comp_number: Optional[str] = None


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    position: Optional[str] = None
    department_id: Optional[str] = None
    salary_base: Optional[float] = None
    employment_status: Optional[str] = None
    bank_account: Optional[str] = None
    tax_id: Optional[str] = None
    napsa_number: Optional[str] = None
    nhima_number: Optional[str] = None


class ContractCreate(BaseModel):
    employee_id: str
    contract_type: str  # permanent, fixed_term, contract, probation
    start_date: date
    end_date: Optional[date] = None
    salary_amount: float
    position_title: str
    department_id: Optional[str] = None
    reporting_to: Optional[str] = None
    leave_days_annual: int = 24
    notes: Optional[str] = None


class JobRequisitionCreate(BaseModel):
    position_title: str
    department_id: str
    number_of_positions: int = 1
    employment_type: str
    salary_band_min: Optional[float] = None
    salary_band_max: Optional[float] = None
    job_description: Optional[str] = None
    required_qualifications: Optional[str] = None
    business_justification: Optional[str] = None


@router.post("/")
def create_employee(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new employee with Zambian compliance fields"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    # Check for duplicate employee number
    existing = db.query(models.Employee).filter(
        models.Employee.company_id == current_user.company_id,
        models.Employee.employee_no == data.employee_no
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Employee number already exists")
    
    # Calculate probation end date if applicable
    probation_end_date = None
    if data.date_joined and data.employment_type in ["permanent", "probation"]:
        probation_end_date = data.date_joined + timedelta(days=90)  # 3 months
    
    # Create onboarding checklist
    onboarding_checklist = [
        {"item": "Upload National ID / Passport", "completed": False},
        {"item": "Provide TPIN number", "completed": False},
        {"item": "Register for NAPSA", "completed": False},
        {"item": "Register for NHIMA", "completed": False},
        {"item": "Submit bank account details", "completed": False},
        {"item": "Sign employment contract", "completed": False},
        {"item": "Complete tax forms", "completed": False},
        {"item": "Emergency contact provided", "completed": False}
    ]
    
    employee = models.Employee(
        company_id=current_user.company_id,
        employee_no=data.employee_no,
        first_name=data.first_name,
        middle_name=data.middle_name,
        last_name=data.last_name,
        maiden_name=data.maiden_name,
        email=data.email,
        phone=data.phone,
        mobile_phone=data.mobile_phone,
        id_number=data.id_number,
        passport_number=data.passport_number,
        date_of_birth=data.date_of_birth,
        gender=data.gender,
        marital_status=data.marital_status,
        nationality=data.nationality,
        residential_address=data.residential_address,
        city=data.city,
        province=data.province,
        position=data.position,
        department_id=data.department_id,
        supervisor_id=data.supervisor_id,
        date_joined=data.date_joined,
        probation_end_date=probation_end_date,
        employment_type=data.employment_type,
        employment_status="probation" if data.employment_type == "probation" else "active",
        salary_base=data.salary_base,
        bank_name=data.bank_name,
        bank_account=data.bank_account,
        tax_id=data.tax_id,
        napsa_number=data.napsa_number,
        nhima_number=data.nhima_number,
        workers_comp_number=data.workers_comp_number,
        onboarding_checklist=onboarding_checklist,
        onboarding_completed=False,
        created_by=current_user.id
    )
    
    db.add(employee)
    db.commit()
    db.refresh(employee)
    
    return {"success": True, "employee": employee}


@router.get("/")
def list_employees(
    department_id: Optional[str] = None,
    employment_status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all employees"""
    query = db.query(models.Employee).filter(
        models.Employee.company_id == current_user.company_id,
        models.Employee.is_active == True
    )
    
    if department_id:
        query = query.filter(models.Employee.department_id == department_id)
    if employment_status:
        query = query.filter(models.Employee.employment_status == employment_status)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.Employee.first_name.ilike(search_term)) |
            (models.Employee.last_name.ilike(search_term)) |
            (models.Employee.employee_no.ilike(search_term)) |
            (models.Employee.email.ilike(search_term))
        )
    
    employees = query.order_by(models.Employee.first_name).all()
    
    return {"success": True, "count": len(employees), "employees": employees}


@router.get("/{employee_id}")
def get_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get employee details"""
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id,
        models.Employee.company_id == current_user.company_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get contracts
    contracts = db.query(models.EmployeeContract).filter(
        models.EmployeeContract.employee_id == employee_id
    ).all()
    
    # Get loans
    loans = db.query(models.EmployeeLoan).filter(
        models.EmployeeLoan.employee_id == employee_id
    ).all()
    
    return {
        "success": True,
        "employee": employee,
        "contracts": contracts,
        "loans": loans
    }


@router.put("/{employee_id}")
def update_employee(
    employee_id: str,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update employee"""
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id,
        models.Employee.company_id == current_user.company_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update fields
    for field, value in data.dict(exclude_unset=True).items():
        setattr(employee, field, value)
    
    employee.updated_at = datetime.now()
    
    db.commit()
    db.refresh(employee)
    
    return {"success": True, "employee": employee}


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Soft delete employee"""
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id,
        models.Employee.company_id == current_user.company_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee.is_active = False
    employee.employment_status = "terminated"
    employee.date_terminated = date.today()
    
    db.commit()
    
    return {"success": True, "message": "Employee deactivated"}


@router.post("/contracts")
def create_contract(
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create employment contract"""
    # Verify employee
    employee = db.query(models.Employee).filter(
        models.Employee.id == data.employee_id,
        models.Employee.company_id == current_user.company_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    contract = models.EmployeeContract(
        company_id=current_user.company_id,
        employee_id=data.employee_id,
        contract_type=data.contract_type,
        start_date=data.start_date,
        end_date=data.end_date,
        salary_amount=data.salary_amount,
        position_title=data.position_title,
        department_id=data.department_id,
        reporting_to=data.reporting_to,
        leave_days_annual=data.leave_days_annual,
        status="draft",
        notes=data.notes,
        created_by=current_user.id
    )
    
    db.add(contract)
    
    # Update employee
    employee.has_employment_contract = True
    
    db.commit()
    db.refresh(contract)
    
    return {"success": True, "contract": contract}


@router.post("/requisitions")
def create_job_requisition(
    data: JobRequisitionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create job requisition"""
    # Generate requisition number
    last_req = db.query(models.JobRequisition).filter(
        models.JobRequisition.company_id == current_user.company_id
    ).order_by(models.JobRequisition.created_at.desc()).first()
    
    if last_req and last_req.requisition_number:
        try:
            last_num = int(last_req.requisition_number.split('-')[1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    requisition_number = f"JR-{new_num:05d}"
    
    requisition = models.JobRequisition(
        company_id=current_user.company_id,
        requisition_number=requisition_number,
        position_title=data.position_title,
        department_id=data.department_id,
        number_of_positions=data.number_of_positions,
        employment_type=data.employment_type,
        salary_band_min=data.salary_band_min,
        salary_band_max=data.salary_band_max,
        job_description=data.job_description,
        required_qualifications=data.required_qualifications,
        business_justification=data.business_justification,
        status="draft",
        created_by=current_user.id
    )
    
    db.add(requisition)
    db.commit()
    db.refresh(requisition)
    
    return {"success": True, "requisition": requisition}


@router.get("/requisitions")
def list_requisitions(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List job requisitions"""
    query = db.query(models.JobRequisition).filter(
        models.JobRequisition.company_id == current_user.company_id
    )
    
    if status:
        query = query.filter(models.JobRequisition.status == status)
    
    requisitions = query.order_by(models.JobRequisition.created_at.desc()).all()
    
    return {"success": True, "count": len(requisitions), "requisitions": requisitions}


@router.get("/onboarding-progress/{employee_id}")
def get_onboarding_progress(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get employee onboarding progress"""
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id,
        models.Employee.company_id == current_user.company_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    checklist = employee.onboarding_checklist or []
    total_items = len(checklist)
    completed_items = sum(1 for item in checklist if item.get("completed", False))
    completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
    
    return {
        "success": True,
        "employee_id": employee_id,
        "employee_name": f"{employee.first_name} {employee.last_name}",
        "onboarding_completed": employee.onboarding_completed,
        "completion_date": employee.onboarding_completion_date,
        "progress": {
            "total_items": total_items,
            "completed_items": completed_items,
            "pending_items": total_items - completed_items,
            "completion_percentage": round(completion_percentage, 2)
        },
        "checklist": checklist
    }


# ============================================================================
# EMPLOYEE DOCUMENT MANAGEMENT
# ============================================================================

@router.post("/{employee_id}/documents/upload")
async def upload_employee_document(
    employee_id: str,
    file: UploadFile = File(...),
    category: str = "other",
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Upload a document for an employee"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    doc_manager = DocumentManager(db)
    
    try:
        result = await doc_manager.upload_document(
            file=file,
            company_id=current_user.company_id,
            employee_id=employee_id,
            document_category=category,
            description=description,
            uploaded_by=current_user.id
        )
        
        return {
            "success": True,
            "message": "Document uploaded successfully",
            "document": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{employee_id}/documents")
def list_employee_documents(
    employee_id: str,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all documents for an employee"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    doc_manager = DocumentManager(db)
    documents = doc_manager.list_employee_documents(
        employee_id=employee_id,
        company_id=current_user.company_id,
        category=category
    )
    
    return {
        "success": True,
        "employee_id": employee_id,
        "documents": documents,
        "count": len(documents)
    }


@router.get("/documents/{document_id}/download")
def download_employee_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Download an employee document"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    doc_manager = DocumentManager(db)
    
    try:
        file_path = doc_manager.get_document_path(document_id, current_user.company_id)
        
        # Get document details for filename
        document = db.query(models.EmployeeDocument).filter(
            models.EmployeeDocument.id == document_id
        ).first()
        
        return FileResponse(
            path=file_path,
            filename=document.document_name if document else "document",
            media_type=document.mime_type if document else "application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
def delete_employee_document(
    document_id: str,
    hard_delete: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete an employee document (soft delete by default)"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    doc_manager = DocumentManager(db)
    
    try:
        doc_manager.delete_document(
            document_id=document_id,
            company_id=current_user.company_id,
            soft_delete=not hard_delete
        )
        
        return {
            "success": True,
            "message": "Document deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/categories")
def get_document_categories(
    current_user: models.User = Depends(get_current_user)
):
    """Get all available document categories"""
    doc_manager = DocumentManager(None)
    categories = doc_manager.get_document_categories()
    
    return {
        "success": True,
        "categories": [
            {"key": key, "label": label}
            for key, label in categories.items()
        ]
    }

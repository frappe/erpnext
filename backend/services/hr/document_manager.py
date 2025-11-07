"""
Employee Document Management Service

Handles secure upload, storage, and retrieval of employee documents:
- Employment contracts
- ID documents (NRC, Passport, Driver's License)
- Tax clearance certificates
- Educational certificates
- Professional certifications
- Performance appraisals
- Disciplinary records
"""

import os
import uuid
import shutil
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
import models

# Configure upload directory
UPLOAD_BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "employee_documents")
os.makedirs(UPLOAD_BASE_DIR, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'bmp',
    'xls', 'xlsx', 'csv', 'txt', 'odt', 'ods'
}

# Document categories
DOCUMENT_CATEGORIES = {
    'contract': 'Employment Contract',
    'id_document': 'ID Document',
    'tax_clearance': 'Tax Clearance',
    'educational_cert': 'Educational Certificate',
    'professional_cert': 'Professional Certification',
    'performance_appraisal': 'Performance Appraisal',
    'disciplinary': 'Disciplinary Record',
    'medical': 'Medical Certificate',
    'photo': 'Employee Photo',
    'cv': 'Curriculum Vitae',
    'other': 'Other Document'
}

# Maximum file size (20MB)
MAX_FILE_SIZE = 20 * 1024 * 1024


class DocumentManager:
    """Manages employee document upload, storage, and retrieval"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file"""
        # Check file extension
        if '.' not in file.filename:
            raise HTTPException(status_code=400, detail="File must have an extension")
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type .{ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size (read first chunk to validate)
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
    
    def generate_secure_filename(self, original_filename: str, company_id: str, employee_id: str) -> str:
        """Generate a secure unique filename"""
        ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'bin'
        unique_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"{company_id}_{employee_id}_{timestamp}_{unique_id}.{ext}"
    
    def get_employee_directory(self, company_id: str, employee_id: str) -> str:
        """Get or create employee document directory"""
        employee_dir = os.path.join(UPLOAD_BASE_DIR, company_id, employee_id)
        os.makedirs(employee_dir, exist_ok=True)
        return employee_dir
    
    async def upload_document(
        self,
        file: UploadFile,
        company_id: str,
        employee_id: str,
        document_category: str,
        description: Optional[str] = None,
        uploaded_by: str = None
    ) -> Dict:
        """
        Upload and store employee document
        
        Returns document metadata
        """
        # Validate inputs
        if document_category not in DOCUMENT_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Allowed: {', '.join(DOCUMENT_CATEGORIES.keys())}"
            )
        
        # Validate employee exists
        employee = self.db.query(models.Employee).filter(
            models.Employee.id == employee_id,
            models.Employee.company_id == company_id
        ).first()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Validate file
        self.validate_file(file)
        
        # Generate secure filename
        secure_filename = self.generate_secure_filename(file.filename, company_id, employee_id)
        employee_dir = self.get_employee_directory(company_id, employee_id)
        file_path = os.path.join(employee_dir, secure_filename)
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
        # Create document record in database
        from models import EmployeeDocument
        document = EmployeeDocument(
            company_id=company_id,
            employee_id=employee_id,
            document_category=document_category,
            document_name=file.filename,
            secure_filename=secure_filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            mime_type=file.content_type,
            description=description,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow()
        )
        
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        
        return {
            "id": document.id,
            "document_name": document.document_name,
            "category": document.document_category,
            "category_name": DOCUMENT_CATEGORIES[document.document_category],
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "description": document.description,
            "uploaded_at": document.uploaded_at.isoformat(),
            "uploaded_by": uploaded_by
        }
    
    def get_document_path(self, document_id: str, company_id: str) -> str:
        """Get physical file path for document with security check"""
        from models import EmployeeDocument
        document = self.db.query(EmployeeDocument).filter(
            EmployeeDocument.id == document_id,
            EmployeeDocument.company_id == company_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not os.path.exists(document.file_path):
            raise HTTPException(status_code=404, detail="Document file not found on disk")
        
        return document.file_path
    
    def list_employee_documents(
        self,
        employee_id: str,
        company_id: str,
        category: Optional[str] = None
    ) -> List[Dict]:
        """List all documents for an employee"""
        from models import EmployeeDocument
        query = self.db.query(EmployeeDocument).filter(
            EmployeeDocument.employee_id == employee_id,
            EmployeeDocument.company_id == company_id,
            EmployeeDocument.is_deleted == False
        )
        
        if category:
            query = query.filter(EmployeeDocument.document_category == category)
        
        documents = query.order_by(EmployeeDocument.uploaded_at.desc()).all()
        
        return [
            {
                "id": doc.id,
                "document_name": doc.document_name,
                "category": doc.document_category,
                "category_name": DOCUMENT_CATEGORIES.get(doc.document_category, doc.document_category),
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "description": doc.description,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "uploaded_by": doc.uploaded_by
            }
            for doc in documents
        ]
    
    def delete_document(self, document_id: str, company_id: str, soft_delete: bool = True) -> bool:
        """Delete or soft-delete a document"""
        from models import EmployeeDocument
        document = self.db.query(EmployeeDocument).filter(
            EmployeeDocument.id == document_id,
            EmployeeDocument.company_id == company_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if soft_delete:
            # Soft delete
            document.is_deleted = True
            document.deleted_at = datetime.utcnow()
            self.db.commit()
        else:
            # Hard delete - remove file and record
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
            self.db.delete(document)
            self.db.commit()
        
        return True
    
    def get_document_categories(self) -> Dict[str, str]:
        """Get all available document categories"""
        return DOCUMENT_CATEGORIES

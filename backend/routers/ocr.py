"""
OCR & Document Processing API Router

Handles document uploads and OCR processing using Claude Vision
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

import models
from database import get_db
from auth import get_current_user
from services.ocr_service import ocr_service

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/process-invoice", response_model=dict)
async def process_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process an invoice image using OCR and extract structured data
    
    Supported formats: JPEG, PNG, PDF (first page)
    """
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: JPEG, PNG, PDF"
        )
    
    # Read file data
    file_data = await file.read()
    
    # Process with OCR service
    result = await ocr_service.process_invoice(file_data, file.content_type)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "OCR processing failed"))
    
    # Log OCR request for audit
    # (In production, you'd store the processed result in database)
    
    return {
        "message": "Invoice processed successfully",
        "filename": file.filename,
        "extracted_data": result.get("data"),
        "confidence": result.get("confidence"),
        "processed_at": result.get("processed_at")
    }


@router.post("/process-receipt", response_model=dict)
async def process_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process a receipt image using OCR and extract structured data
    """
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: JPEG, PNG"
        )
    
    # Read file data
    file_data = await file.read()
    
    # Process with OCR service
    result = await ocr_service.process_receipt(file_data, file.content_type)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "OCR processing failed"))
    
    return {
        "message": "Receipt processed successfully",
        "filename": file.filename,
        "extracted_data": result.get("data"),
        "processed_at": result.get("processed_at")
    }


@router.post("/extract-text", response_model=dict)
async def extract_text(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Extract all text from an image using OCR
    """
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: JPEG, PNG, PDF"
        )
    
    # Read file data
    file_data = await file.read()
    
    # Process with OCR service
    result = await ocr_service.extract_text(file_data, file.content_type)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Text extraction failed"))
    
    return {
        "message": "Text extracted successfully",
        "filename": file.filename,
        "text": result.get("text"),
        "processed_at": result.get("processed_at")
    }

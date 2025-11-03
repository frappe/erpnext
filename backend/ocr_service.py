import anthropic
import os
import base64
import json
from datetime import datetime
from typing import Dict, Any, Optional

class OCRService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    def process_document(self, file_path: str, document_type: str) -> Dict[str, Any]:
        """Process document with Claude AI Vision to extract structured data"""
        
        with open(file_path, "rb") as f:
            file_data = f.read()
            file_base64 = base64.b64encode(file_data).decode('utf-8')
        
        mime_type = self._get_mime_type(file_path)
        
        if document_type == "invoice":
            prompt = self._get_invoice_extraction_prompt()
        elif document_type == "receipt":
            prompt = self._get_receipt_extraction_prompt()
        else:
            prompt = self._get_generic_extraction_prompt()
        
        start_time = datetime.now()
        
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": file_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        extracted_text = message.content[0].text
        
        try:
            structured_data = json.loads(extracted_text)
            confidence_score = structured_data.get('confidence_score', 85.0)
        except json.JSONDecodeError:
            structured_data = {"raw_text": extracted_text, "error": "Failed to parse JSON"}
            confidence_score = 50.0
        
        return {
            "extracted_text": extracted_text,
            "structured_data": structured_data,
            "confidence_score": confidence_score,
            "processing_time_ms": processing_time,
            "ai_model": "claude-3.5-sonnet-20241022"
        }
    
    def _get_invoice_extraction_prompt(self) -> str:
        return """Analyze this invoice image and extract ALL structured data in JSON format.

Return a JSON object with this exact structure:
{
    "confidence_score": 95.0,
    "supplier": {
        "name": "Supplier Company Name",
        "tax_id": "TPIN or VAT number",
        "address": "Full supplier address",
        "phone": "Phone number",
        "email": "Email address"
    },
    "invoice_details": {
        "invoice_number": "INV-12345",
        "invoice_date": "2025-11-03",
        "due_date": "2025-12-03",
        "purchase_order_number": "PO-9876"
    },
    "financial": {
        "currency": "ZMW",
        "subtotal": 5000.00,
        "tax_amount": 800.00,
        "total_amount": 5800.00,
        "amount_paid": 0.00,
        "amount_due": 5800.00
    },
    "line_items": [
        {
            "description": "Product/Service description",
            "quantity": 10.0,
            "unit_price": 500.00,
            "amount": 5000.00,
            "tax_rate": 16.0
        }
    ]
}

Instructions:
- Extract ALL visible text accurately
- Use null for missing fields
- Convert dates to YYYY-MM-DD format
- Calculate totals if not visible
- Provide confidence_score (0-100) based on image quality and data completeness
- Include ALL line items found on the invoice
- If currency symbol is K or ZMK, use "ZMW" (Zambian Kwacha)

Return ONLY valid JSON, no additional text."""
    
    def _get_receipt_extraction_prompt(self) -> str:
        return """Analyze this receipt image and extract ALL structured data in JSON format.

Return a JSON object with this exact structure:
{
    "confidence_score": 95.0,
    "merchant": {
        "name": "Merchant/Store Name",
        "address": "Store address",
        "phone": "Phone number",
        "tax_id": "TPIN if visible"
    },
    "receipt_details": {
        "receipt_number": "Receipt #",
        "receipt_date": "2025-11-03",
        "receipt_time": "14:30:00"
    },
    "financial": {
        "currency": "ZMW",
        "subtotal": 150.00,
        "tax_amount": 24.00,
        "tip_amount": 0.00,
        "total_amount": 174.00
    },
    "payment": {
        "payment_method": "cash or card or mobile_money",
        "card_last_four": "1234"
    },
    "line_items": [
        {
            "description": "Item description",
            "quantity": 2.0,
            "unit_price": 75.00,
            "amount": 150.00
        }
    ],
    "expense_category": "meals_entertainment or office_supplies or transport or utilities",
    "category_confidence": 90.0
}

Instructions:
- Extract ALL visible text accurately
- Use null for missing fields
- Convert dates to YYYY-MM-DD format, times to HH:MM:SS
- Suggest appropriate expense_category based on merchant type and items
- Provide confidence scores (0-100)
- Include ALL line items
- If currency symbol is K or ZMK, use "ZMW" (Zambian Kwacha)

Common expense categories:
- meals_entertainment
- office_supplies
- transport
- utilities
- marketing
- professional_services
- rent
- maintenance
- other

Return ONLY valid JSON, no additional text."""
    
    def _get_generic_extraction_prompt(self) -> str:
        return """Analyze this document image and extract ALL structured data in JSON format.

Return a JSON object with the extracted information, including:
- confidence_score (0-100)
- document_type (if identifiable)
- key_data (all extracted key-value pairs)
- line_items (if applicable)
- dates (all dates found)
- amounts (all monetary amounts found)
- entities (people, companies, addresses)

Return ONLY valid JSON, no additional text."""
    
    def _get_mime_type(self, file_path: str) -> str:
        """Detect MIME type from file extension"""
        ext = file_path.lower().split('.')[-1]
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'pdf': 'application/pdf'
        }
        return mime_types.get(ext, 'image/jpeg')
    
    def match_supplier(self, extracted_data: Dict[str, Any], suppliers: list) -> Optional[Dict[str, Any]]:
        """Match extracted supplier data with existing suppliers using fuzzy matching"""
        if not extracted_data.get('supplier') or not suppliers:
            return None
        
        extracted_supplier = extracted_data['supplier']
        supplier_name = extracted_supplier.get('name', '').lower()
        supplier_tax_id = extracted_supplier.get('tax_id', '').lower()
        
        best_match = None
        best_score = 0.0
        
        for supplier in suppliers:
            score = 0.0
            
            if supplier_tax_id and supplier.tax_id and supplier_tax_id == supplier.tax_id.lower():
                score = 100.0
            elif supplier_name and supplier.name:
                name_lower = supplier.name.lower()
                if supplier_name == name_lower:
                    score = 95.0
                elif supplier_name in name_lower or name_lower in supplier_name:
                    score = 75.0
                else:
                    common_words = set(supplier_name.split()) & set(name_lower.split())
                    if common_words:
                        score = 50.0 + (len(common_words) * 10.0)
            
            if score > best_score:
                best_score = score
                best_match = {
                    "supplier_id": supplier.id,
                    "confidence": best_score
                }
        
        return best_match if best_score >= 50.0 else None
    
    def suggest_expense_category(self, receipt_data: Dict[str, Any]) -> tuple:
        """Suggest expense category based on receipt data (AI already suggests, this validates)"""
        suggested = receipt_data.get('expense_category', 'other')
        confidence = receipt_data.get('category_confidence', 70.0)
        
        valid_categories = [
            'meals_entertainment', 'office_supplies', 'transport', 'utilities',
            'marketing', 'professional_services', 'rent', 'maintenance', 
            'travel', 'communications', 'insurance', 'other'
        ]
        
        if suggested not in valid_categories:
            suggested = 'other'
            confidence = 50.0
        
        return suggested, confidence

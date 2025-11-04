"""
OCR & Document Intelligence Service

Uses Claude Vision API for document processing, invoice scanning, and data extraction
"""

import os
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
import json


class OCRService:
    """OCR service using Claude Vision for document processing"""
    
    def __init__(self):
        # Claude API is already configured via python_anthropic_ai_integrations
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        
    async def process_invoice(self, image_data: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """
        Process an invoice image and extract structured data
        
        Returns invoice fields: supplier, amount, date, line items, etc.
        """
        try:
            # Import anthropic here to avoid import errors if not installed
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Create prompt for invoice extraction
            prompt = """
            Analyze this invoice image and extract the following information in JSON format:
            
            {
                "supplier_name": "Company name",
                "supplier_tax_id": "Tax ID or TPIN",
                "invoice_number": "Invoice number",
                "invoice_date": "Date (YYYY-MM-DD format)",
                "due_date": "Due date (YYYY-MM-DD format)",
                "currency": "Currency code (e.g., ZMW, USD)",
                "subtotal": 0.00,
                "tax_amount": 0.00,
                "total_amount": 0.00,
                "line_items": [
                    {
                        "description": "Item description",
                        "quantity": 0,
                        "unit_price": 0.00,
                        "amount": 0.00
                    }
                ]
            }
            
            Extract all visible information. If a field is not found, use null.
            Return only valid JSON, no additional text.
            """
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )
            
            # Parse response
            response_text = message.content[0].text
            
            # Extract JSON from response
            try:
                # Try to find JSON in response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    extracted_data = json.loads(json_text)
                else:
                    extracted_data = json.loads(response_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw response
                extracted_data = {"raw_response": response_text, "error": "Failed to parse JSON"}
            
            return {
                "success": True,
                "data": extracted_data,
                "confidence": "high",  # Claude is generally high confidence
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def process_receipt(self, image_data: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """
        Process a receipt image and extract structured data
        """
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            prompt = """
            Analyze this receipt image and extract the following information in JSON format:
            
            {
                "merchant_name": "Store/merchant name",
                "receipt_number": "Receipt number",
                "date": "Date (YYYY-MM-DD format)",
                "time": "Time (HH:MM format)",
                "currency": "Currency code",
                "items": [
                    {
                        "description": "Item name",
                        "quantity": 1,
                        "unit_price": 0.00,
                        "amount": 0.00
                    }
                ],
                "subtotal": 0.00,
                "tax": 0.00,
                "total": 0.00,
                "payment_method": "cash/card/mobile money"
            }
            
            Return only valid JSON, no additional text.
            """
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )
            
            response_text = message.content[0].text
            
            # Extract JSON
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    extracted_data = json.loads(json_text)
                else:
                    extracted_data = json.loads(response_text)
            except json.JSONDecodeError:
                extracted_data = {"raw_response": response_text, "error": "Failed to parse JSON"}
            
            return {
                "success": True,
                "data": extracted_data,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def extract_text(self, image_data: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """
        Extract all text from an image using OCR
        """
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": "Extract all visible text from this image. Return the text exactly as it appears, preserving formatting and layout as much as possible."
                            }
                        ],
                    }
                ],
            )
            
            extracted_text = message.content[0].text
            
            return {
                "success": True,
                "text": extracted_text,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": None
            }


# Singleton instance
ocr_service = OCRService()

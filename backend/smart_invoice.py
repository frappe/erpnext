"""
Smart Invoice Compliance System

Features:
1. QR Code Generation with ZRA-compliant data
2. UBL XML Export for electronic invoicing
3. ZRA Invoice Validation
4. Invoice verification codes
"""

import qrcode
import io
import base64
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, Any
import hashlib
import xml.etree.ElementTree as ET
from xml.dom import minidom


class SmartInvoiceService:
    """Service for Smart Invoice compliance features"""
    
    def __init__(self):
        self.zra_namespace = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
        
    def generate_invoice_qr_code(self, invoice_data: Dict[str, Any]) -> str:
        """
        Generate QR code for invoice with ZRA-compliant data
        
        QR Code contains:
        - Invoice Number
        - Date
        - Total Amount
        - Tax Amount
        - Seller TPIN
        - Buyer TPIN (if available)
        - Verification Code
        """
        
        verification_code = self._generate_verification_code(invoice_data)
        
        qr_data = {
            "inv_no": invoice_data.get("invoice_number", ""),
            "date": invoice_data.get("invoice_date", ""),
            "total": invoice_data.get("total_amount", 0),
            "tax": invoice_data.get("tax_amount", 0),
            "seller_tpin": invoice_data.get("seller_tpin", ""),
            "buyer_tpin": invoice_data.get("buyer_tpin", ""),
            "verification": verification_code
        }
        
        qr_string = "|".join([
            f"INV:{qr_data['inv_no']}",
            f"DATE:{qr_data['date']}",
            f"TOTAL:{qr_data['total']}",
            f"TAX:{qr_data['tax']}",
            f"SELLER:{qr_data['seller_tpin']}",
            f"BUYER:{qr_data['buyer_tpin']}",
            f"VER:{qr_data['verification']}"
        ])
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_string)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{qr_code_base64}"
    
    def _generate_verification_code(self, invoice_data: Dict[str, Any]) -> str:
        """Generate verification code for invoice"""
        data_string = f"{invoice_data.get('invoice_number', '')}" \
                     f"{invoice_data.get('invoice_date', '')}" \
                     f"{invoice_data.get('total_amount', 0)}" \
                     f"{invoice_data.get('seller_tpin', '')}"
        
        hash_object = hashlib.sha256(data_string.encode())
        return hash_object.hexdigest()[:12].upper()
    
    def export_to_ubl_xml(self, invoice_data: Dict[str, Any]) -> str:
        """
        Export invoice to UBL 2.1 XML format (ZRA electronic invoicing)
        
        UBL (Universal Business Language) is required for ZRA electronic submissions
        """
        
        root = ET.Element("Invoice", xmlns=self.zra_namespace)
        
        ET.SubElement(root, "UBLVersionID").text = "2.1"
        ET.SubElement(root, "CustomizationID").text = "ZRA-Zambia"
        ET.SubElement(root, "ID").text = invoice_data.get("invoice_number", "")
        ET.SubElement(root, "IssueDate").text = invoice_data.get("invoice_date", "")
        ET.SubElement(root, "InvoiceTypeCode").text = "380"
        ET.SubElement(root, "DocumentCurrencyCode").text = invoice_data.get("currency", "ZMW")
        
        supplier = ET.SubElement(root, "AccountingSupplierParty")
        supplier_party = ET.SubElement(supplier, "Party")
        supplier_id = ET.SubElement(supplier_party, "PartyIdentification")
        ET.SubElement(supplier_id, "ID", schemeID="TPIN").text = invoice_data.get("seller_tpin", "")
        supplier_name = ET.SubElement(supplier_party, "PartyName")
        ET.SubElement(supplier_name, "Name").text = invoice_data.get("seller_name", "")
        
        if invoice_data.get("buyer_tpin"):
            customer = ET.SubElement(root, "AccountingCustomerParty")
            customer_party = ET.SubElement(customer, "Party")
            customer_id = ET.SubElement(customer_party, "PartyIdentification")
            ET.SubElement(customer_id, "ID", schemeID="TPIN").text = invoice_data.get("buyer_tpin", "")
            customer_name = ET.SubElement(customer_party, "PartyName")
            ET.SubElement(customer_name, "Name").text = invoice_data.get("buyer_name", "")
        
        tax_total = ET.SubElement(root, "TaxTotal")
        ET.SubElement(tax_total, "TaxAmount", currencyID=invoice_data.get("currency", "ZMW")).text = \
            str(invoice_data.get("tax_amount", 0))
        
        tax_subtotal = ET.SubElement(tax_total, "TaxSubtotal")
        ET.SubElement(tax_subtotal, "TaxableAmount", currencyID=invoice_data.get("currency", "ZMW")).text = \
            str(invoice_data.get("subtotal", 0))
        ET.SubElement(tax_subtotal, "TaxAmount", currencyID=invoice_data.get("currency", "ZMW")).text = \
            str(invoice_data.get("tax_amount", 0))
        
        tax_category = ET.SubElement(tax_subtotal, "TaxCategory")
        ET.SubElement(tax_category, "ID").text = "S"
        ET.SubElement(tax_category, "Percent").text = str(invoice_data.get("tax_rate", 16))
        tax_scheme = ET.SubElement(tax_category, "TaxScheme")
        ET.SubElement(tax_scheme, "ID").text = "VAT"
        
        legal_monetary_total = ET.SubElement(root, "LegalMonetaryTotal")
        ET.SubElement(legal_monetary_total, "LineExtensionAmount", 
                     currencyID=invoice_data.get("currency", "ZMW")).text = \
            str(invoice_data.get("subtotal", 0))
        ET.SubElement(legal_monetary_total, "TaxExclusiveAmount", 
                     currencyID=invoice_data.get("currency", "ZMW")).text = \
            str(invoice_data.get("subtotal", 0))
        ET.SubElement(legal_monetary_total, "TaxInclusiveAmount", 
                     currencyID=invoice_data.get("currency", "ZMW")).text = \
            str(invoice_data.get("total_amount", 0))
        ET.SubElement(legal_monetary_total, "PayableAmount", 
                     currencyID=invoice_data.get("currency", "ZMW")).text = \
            str(invoice_data.get("total_amount", 0))
        
        for idx, line in enumerate(invoice_data.get("lines", []), 1):
            invoice_line = ET.SubElement(root, "InvoiceLine")
            ET.SubElement(invoice_line, "ID").text = str(idx)
            ET.SubElement(invoice_line, "InvoicedQuantity", unitCode="EA").text = \
                str(line.get("quantity", 1))
            ET.SubElement(invoice_line, "LineExtensionAmount", 
                         currencyID=invoice_data.get("currency", "ZMW")).text = \
                str(line.get("amount", 0))
            
            item = ET.SubElement(invoice_line, "Item")
            ET.SubElement(item, "Description").text = line.get("description", "")
            ET.SubElement(item, "Name").text = line.get("name", "")
            
            price = ET.SubElement(invoice_line, "Price")
            ET.SubElement(price, "PriceAmount", 
                         currencyID=invoice_data.get("currency", "ZMW")).text = \
                str(line.get("unit_price", 0))
        
        xml_string = ET.tostring(root, encoding='unicode')
        
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        return pretty_xml
    
    def validate_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate invoice against ZRA requirements
        
        ZRA Requirements:
        - Seller TPIN must be present and valid format
        - Invoice number must be unique and sequential
        - Tax calculations must be accurate
        - Required fields must be present
        """
        
        errors = []
        warnings = []
        
        if not invoice_data.get("seller_tpin"):
            errors.append("Seller TPIN is required")
        elif not self._validate_tpin_format(invoice_data.get("seller_tpin")):
            errors.append("Seller TPIN format is invalid")
        
        if not invoice_data.get("invoice_number"):
            errors.append("Invoice number is required")
        
        if not invoice_data.get("invoice_date"):
            errors.append("Invoice date is required")
        
        if invoice_data.get("buyer_tpin") and not self._validate_tpin_format(invoice_data.get("buyer_tpin")):
            warnings.append("Buyer TPIN format appears invalid")
        
        subtotal = Decimal(str(invoice_data.get("subtotal", 0)))
        tax_rate = Decimal(str(invoice_data.get("tax_rate", 16))) / 100
        calculated_tax = subtotal * tax_rate
        reported_tax = Decimal(str(invoice_data.get("tax_amount", 0)))
        
        if abs(calculated_tax - reported_tax) > Decimal("0.01"):
            errors.append(f"Tax calculation mismatch. Expected: {calculated_tax}, Got: {reported_tax}")
        
        total = subtotal + reported_tax
        reported_total = Decimal(str(invoice_data.get("total_amount", 0)))
        
        if abs(total - reported_total) > Decimal("0.01"):
            errors.append(f"Total amount mismatch. Expected: {total}, Got: {reported_total}")
        
        is_valid = len(errors) == 0
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "verification_code": self._generate_verification_code(invoice_data) if is_valid else None
        }
    
    def _validate_tpin_format(self, tpin: str) -> bool:
        """Validate Zambian TPIN format (10 digits)"""
        if not tpin:
            return False
        
        tpin_clean = tpin.replace("-", "").replace(" ", "")
        
        return tpin_clean.isdigit() and len(tpin_clean) == 10
    
    def generate_zra_submission_package(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete ZRA submission package
        
        Returns:
        - UBL XML
        - QR Code
        - Validation report
        - Verification code
        """
        
        validation = self.validate_invoice(invoice_data)
        
        if not validation["is_valid"]:
            return {
                "success": False,
                "errors": validation["errors"],
                "warnings": validation["warnings"]
            }
        
        ubl_xml = self.export_to_ubl_xml(invoice_data)
        qr_code = self.generate_invoice_qr_code(invoice_data)
        
        return {
            "success": True,
            "validation": validation,
            "ubl_xml": ubl_xml,
            "qr_code": qr_code,
            "verification_code": validation["verification_code"],
            "warnings": validation["warnings"]
        }

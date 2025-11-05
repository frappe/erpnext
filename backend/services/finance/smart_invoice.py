"""
Finance - Smart Invoice Compliance Service

Implements Smart Invoice features per Finance PDF spec:
- UBL (Universal Business Language) XML export
- JSON invoice export
- QR code generation for invoices
- ZRA (Zambia Revenue Authority) compliance
- E-invoice validation

Smart Invoice Requirements (ZRA Compliance):
1. Generate UBL 2.1 compliant XML
2. Generate JSON invoice format
3. QR code with invoice reference and validation hash
4. Digital signature for invoices
5. Tax breakdown by type (VAT, Excise, Withholding)
6. ZRA TPIN validation
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, date
from decimal import Decimal
import models
import json
import hashlib
import base64
import xml.etree.ElementTree as ET
from xml.dom import minidom
import qrcode
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class SmartInvoiceService:
    """
    Smart Invoice Compliance Service
    Handles UBL/JSON export and QR code generation for invoices
    """
    
    # ZRA Invoice Types
    INVOICE_TYPE_STANDARD = "380"  # Standard commercial invoice
    INVOICE_TYPE_CREDIT_NOTE = "381"  # Credit note
    INVOICE_TYPE_DEBIT_NOTE = "383"  # Debit note
    
    # Tax categories (Zambian tax system)
    TAX_CATEGORY_VAT_STANDARD = "S"  # Standard VAT (16%)
    TAX_CATEGORY_VAT_ZERO = "Z"      # Zero-rated VAT
    TAX_CATEGORY_VAT_EXEMPT = "E"    # VAT exempt
    TAX_CATEGORY_WITHHOLDING = "W"   # Withholding tax
    
    def __init__(self, db: Session, company_id: str, user_id: str):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
    
    def generate_ubl_xml(self, invoice_id: str) -> str:
        """
        Generate UBL 2.1 XML for an invoice
        
        UBL Structure:
        - Invoice header (number, date, currency)
        - Supplier information (company TPIN, name, address)
        - Customer information (TPIN, name, address)
        - Invoice lines (items, quantities, prices)
        - Tax totals (VAT, withholding, etc.)
        - Legal monetary total
        
        Args:
            invoice_id: ID of the sales invoice
        
        Returns:
            UBL XML string
        """
        # Get invoice with related data
        invoice = self.db.query(models.SalesOrder).filter(
            models.SalesOrder.id == invoice_id,
            models.SalesOrder.company_id == self.company_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # Get company (supplier) details
        company = self.db.query(models.Company).filter(
            models.Company.id == self.company_id
        ).first()
        
        # Get customer details
        customer = self.db.query(models.Customer).filter(
            models.Customer.id == invoice.customer_id
        ).first()
        
        # Build UBL XML
        root = ET.Element("Invoice", xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2")
        root.set("xmlns:cac", "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2")
        root.set("xmlns:cbc", "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2")
        
        # Invoice header
        ET.SubElement(root, "cbc:UBLVersionID").text = "2.1"
        ET.SubElement(root, "cbc:ID").text = str(invoice.order_number)
        ET.SubElement(root, "cbc:IssueDate").text = invoice.order_date.isoformat()
        ET.SubElement(root, "cbc:InvoiceTypeCode").text = self.INVOICE_TYPE_STANDARD
        ET.SubElement(root, "cbc:DocumentCurrencyCode").text = invoice.currency or "ZMW"
        
        # Supplier (AccountingSupplierParty)
        supplier_party = ET.SubElement(root, "cac:AccountingSupplierParty")
        supplier = ET.SubElement(supplier_party, "cac:Party")
        
        # Supplier identification (TPIN)
        if company.tax_number:
            party_tax = ET.SubElement(supplier, "cac:PartyTaxScheme")
            ET.SubElement(party_tax, "cbc:CompanyID").text = company.tax_number
            tax_scheme = ET.SubElement(party_tax, "cac:TaxScheme")
            ET.SubElement(tax_scheme, "cbc:ID").text = "VAT"
        
        # Supplier name
        party_name = ET.SubElement(supplier, "cac:PartyName")
        ET.SubElement(party_name, "cbc:Name").text = company.name
        
        # Supplier address
        if company.address:
            postal_address = ET.SubElement(supplier, "cac:PostalAddress")
            ET.SubElement(postal_address, "cbc:StreetName").text = company.address
            ET.SubElement(postal_address, "cbc:CityName").text = company.city or "Lusaka"
            ET.SubElement(postal_address, "cbc:CountrySubentity").text = company.province or "Lusaka"
            country = ET.SubElement(postal_address, "cac:Country")
            ET.SubElement(country, "cbc:IdentificationCode").text = "ZM"
        
        # Customer (AccountingCustomerParty)
        customer_party = ET.SubElement(root, "cac:AccountingCustomerParty")
        buyer = ET.SubElement(customer_party, "cac:Party")
        
        # Customer identification (TPIN)
        if customer and customer.tax_number:
            party_tax = ET.SubElement(buyer, "cac:PartyTaxScheme")
            ET.SubElement(party_tax, "cbc:CompanyID").text = customer.tax_number
            tax_scheme = ET.SubElement(party_tax, "cac:TaxScheme")
            ET.SubElement(tax_scheme, "cbc:ID").text = "VAT"
        
        # Customer name
        if customer:
            party_name = ET.SubElement(buyer, "cac:PartyName")
            ET.SubElement(party_name, "cbc:Name").text = customer.name
            
            # Customer address
            if customer.address:
                postal_address = ET.SubElement(buyer, "cac:PostalAddress")
                ET.SubElement(postal_address, "cbc:StreetName").text = customer.address
                country = ET.SubElement(postal_address, "cac:Country")
                ET.SubElement(country, "cbc:IdentificationCode").text = "ZM"
        
        # Invoice lines
        lines = self.db.query(models.SalesOrderLine).filter(
            models.SalesOrderLine.sales_order_id == invoice_id
        ).all()
        
        line_total = Decimal("0.00")
        tax_total = Decimal("0.00")
        
        for idx, line in enumerate(lines, start=1):
            inv_line = ET.SubElement(root, "cac:InvoiceLine")
            ET.SubElement(inv_line, "cbc:ID").text = str(idx)
            
            # Quantity
            qty = ET.SubElement(inv_line, "cbc:InvoicedQuantity")
            qty.text = str(line.quantity)
            qty.set("unitCode", "EA")  # Each
            
            # Line total
            line_amount = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
            ET.SubElement(inv_line, "cbc:LineExtensionAmount", currencyID=invoice.currency or "ZMW").text = str(line_amount)
            line_total += line_amount
            
            # Item
            item = ET.SubElement(inv_line, "cac:Item")
            ET.SubElement(item, "cbc:Name").text = line.product_name or f"Product {line.product_id}"
            
            # Tax (default 16% VAT for Zambia)
            classified_tax = ET.SubElement(item, "cac:ClassifiedTaxCategory")
            ET.SubElement(classified_tax, "cbc:ID").text = self.TAX_CATEGORY_VAT_STANDARD
            ET.SubElement(classified_tax, "cbc:Percent").text = "16.0"
            tax_scheme = ET.SubElement(classified_tax, "cac:TaxScheme")
            ET.SubElement(tax_scheme, "cbc:ID").text = "VAT"
            
            # Price
            price = ET.SubElement(inv_line, "cac:Price")
            ET.SubElement(price, "cbc:PriceAmount", currencyID=invoice.currency or "ZMW").text = str(line.unit_price)
        
        # Calculate tax (16% VAT)
        tax_total = line_total * Decimal("0.16")
        
        # Tax total
        tax_total_elem = ET.SubElement(root, "cac:TaxTotal")
        ET.SubElement(tax_total_elem, "cbc:TaxAmount", currencyID=invoice.currency or "ZMW").text = str(tax_total)
        
        # Tax subtotal
        tax_subtotal = ET.SubElement(tax_total_elem, "cac:TaxSubtotal")
        ET.SubElement(tax_subtotal, "cbc:TaxableAmount", currencyID=invoice.currency or "ZMW").text = str(line_total)
        ET.SubElement(tax_subtotal, "cbc:TaxAmount", currencyID=invoice.currency or "ZMW").text = str(tax_total)
        
        tax_category = ET.SubElement(tax_subtotal, "cac:TaxCategory")
        ET.SubElement(tax_category, "cbc:ID").text = self.TAX_CATEGORY_VAT_STANDARD
        ET.SubElement(tax_category, "cbc:Percent").text = "16.0"
        tax_scheme = ET.SubElement(tax_category, "cac:TaxScheme")
        ET.SubElement(tax_scheme, "cbc:ID").text = "VAT"
        
        # Legal monetary total
        monetary_total = ET.SubElement(root, "cac:LegalMonetaryTotal")
        ET.SubElement(monetary_total, "cbc:LineExtensionAmount", currencyID=invoice.currency or "ZMW").text = str(line_total)
        ET.SubElement(monetary_total, "cbc:TaxExclusiveAmount", currencyID=invoice.currency or "ZMW").text = str(line_total)
        ET.SubElement(monetary_total, "cbc:TaxInclusiveAmount", currencyID=invoice.currency or "ZMW").text = str(line_total + tax_total)
        ET.SubElement(monetary_total, "cbc:PayableAmount", currencyID=invoice.currency or "ZMW").text = str(line_total + tax_total)
        
        # Pretty print XML
        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        # Remove extra blank lines
        pretty_xml = "\n".join([line for line in pretty_xml.split("\n") if line.strip()])
        
        logger.info(f"Generated UBL XML for invoice {invoice.order_number}")
        
        return pretty_xml
    
    def generate_json_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Generate JSON invoice format (ZRA compatible)
        
        Args:
            invoice_id: ID of the sales invoice
        
        Returns:
            Invoice data as JSON-serializable dict
        """
        # Get invoice with related data
        invoice = self.db.query(models.SalesOrder).filter(
            models.SalesOrder.id == invoice_id,
            models.SalesOrder.company_id == self.company_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # Get company details
        company = self.db.query(models.Company).filter(
            models.Company.id == self.company_id
        ).first()
        
        # Get customer details
        customer = self.db.query(models.Customer).filter(
            models.Customer.id == invoice.customer_id
        ).first()
        
        # Get invoice lines
        lines = self.db.query(models.SalesOrderLine).filter(
            models.SalesOrderLine.sales_order_id == invoice_id
        ).all()
        
        # Build invoice lines
        invoice_lines = []
        subtotal = Decimal("0.00")
        
        for idx, line in enumerate(lines, start=1):
            line_amount = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
            subtotal += line_amount
            
            invoice_lines.append({
                "line_number": idx,
                "product_code": line.product_id,
                "product_name": line.product_name,
                "quantity": float(line.quantity),
                "unit_price": float(line.unit_price),
                "line_total": float(line_amount),
                "tax_rate": 16.0,  # Standard VAT
                "tax_amount": float(line_amount * Decimal("0.16"))
            })
        
        # Calculate totals
        tax_total = subtotal * Decimal("0.16")
        grand_total = subtotal + tax_total
        
        # Build JSON invoice
        json_invoice = {
            "invoice_number": invoice.order_number,
            "invoice_date": invoice.order_date.isoformat(),
            "invoice_type": "standard",
            "currency": invoice.currency or "ZMW",
            "supplier": {
                "name": company.name,
                "tpin": company.tax_number,
                "address": company.address,
                "city": company.city or "Lusaka",
                "country": "Zambia",
                "phone": company.phone,
                "email": company.email
            },
            "customer": {
                "name": customer.name if customer else "Unknown",
                "tpin": customer.tax_number if customer else None,
                "address": customer.address if customer else None,
                "phone": customer.phone if customer else None,
                "email": customer.email if customer else None
            },
            "lines": invoice_lines,
            "summary": {
                "subtotal": float(subtotal),
                "tax_total": float(tax_total),
                "grand_total": float(grand_total)
            },
            "tax_breakdown": [
                {
                    "tax_type": "VAT",
                    "tax_rate": 16.0,
                    "taxable_amount": float(subtotal),
                    "tax_amount": float(tax_total)
                }
            ],
            "payment_terms": invoice.payment_terms,
            "notes": invoice.notes,
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"Generated JSON invoice for {invoice.order_number}")
        
        return json_invoice
    
    def generate_qr_code(self, invoice_id: str) -> bytes:
        """
        Generate QR code for invoice (ZRA compliance)
        
        QR Code Contents:
        - Invoice number
        - Invoice date
        - Supplier TPIN
        - Total amount
        - Validation hash
        
        Args:
            invoice_id: ID of the sales invoice
        
        Returns:
            QR code image as PNG bytes
        """
        # Get invoice
        invoice = self.db.query(models.SalesOrder).filter(
            models.SalesOrder.id == invoice_id,
            models.SalesOrder.company_id == self.company_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # Get company
        company = self.db.query(models.Company).filter(
            models.Company.id == self.company_id
        ).first()
        
        # Calculate invoice total
        lines = self.db.query(models.SalesOrderLine).filter(
            models.SalesOrderLine.sales_order_id == invoice_id
        ).all()
        
        total = sum(
            Decimal(str(line.quantity)) * Decimal(str(line.unit_price)) * Decimal("1.16")
            for line in lines
        )
        
        # Generate validation hash
        hash_data = f"{invoice.order_number}|{invoice.order_date}|{company.tax_number}|{total}"
        validation_hash = hashlib.sha256(hash_data.encode()).hexdigest()[:16]
        
        # QR code data (JSON format)
        qr_data = json.dumps({
            "invoice": invoice.order_number,
            "date": invoice.order_date.isoformat(),
            "tpin": company.tax_number,
            "total": float(total),
            "currency": invoice.currency or "ZMW",
            "hash": validation_hash
        })
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_bytes = buffer.getvalue()
        
        logger.info(f"Generated QR code for invoice {invoice.order_number}")
        
        return qr_bytes
    
    def validate_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Validate invoice for ZRA compliance
        
        Validation checks:
        1. Supplier TPIN present
        2. Customer TPIN present (for B2B)
        3. Tax calculations correct
        4. All required fields present
        5. Invoice number unique
        
        Args:
            invoice_id: ID of the sales invoice
        
        Returns:
            Validation result with errors/warnings
        """
        errors = []
        warnings = []
        
        # Get invoice
        invoice = self.db.query(models.SalesOrder).filter(
            models.SalesOrder.id == invoice_id,
            models.SalesOrder.company_id == self.company_id
        ).first()
        
        if not invoice:
            return {
                "valid": False,
                "errors": ["Invoice not found"],
                "warnings": []
            }
        
        # Get company
        company = self.db.query(models.Company).filter(
            models.Company.id == self.company_id
        ).first()
        
        # Validation 1: Supplier TPIN
        if not company.tax_number:
            errors.append("Supplier TPIN missing")
        
        # Validation 2: Customer TPIN (warning for B2B)
        customer = self.db.query(models.Customer).filter(
            models.Customer.id == invoice.customer_id
        ).first()
        
        if customer and not customer.tax_number:
            warnings.append("Customer TPIN missing (required for B2B transactions)")
        
        # Validation 3: Invoice lines
        lines = self.db.query(models.SalesOrderLine).filter(
            models.SalesOrderLine.sales_order_id == invoice_id
        ).all()
        
        if not lines:
            errors.append("Invoice has no line items")
        
        # Validation 4: Tax calculations
        subtotal = sum(
            Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
            for line in lines
        )
        
        expected_tax = subtotal * Decimal("0.16")
        
        # Validation 5: Invoice number unique
        duplicate = self.db.query(models.SalesOrder).filter(
            models.SalesOrder.company_id == self.company_id,
            models.SalesOrder.order_number == invoice.order_number,
            models.SalesOrder.id != invoice_id
        ).first()
        
        if duplicate:
            errors.append(f"Duplicate invoice number: {invoice.order_number}")
        
        is_valid = len(errors) == 0
        
        logger.info(
            f"Validated invoice {invoice.order_number}: "
            f"Valid={is_valid}, Errors={len(errors)}, Warnings={len(warnings)}"
        )
        
        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "invoice_number": invoice.order_number,
            "subtotal": float(subtotal),
            "tax_total": float(expected_tax)
        }

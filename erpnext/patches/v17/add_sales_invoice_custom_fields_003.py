"""
Patch: Add custom fields to Sales Invoice
Version: v17
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Add custom fields to Sales Invoice"""
    
    print("\nRunning Patch: Add Sales Invoice Custom Fields (v17)")
    
    custom_fields = {
        "Sales Invoice": [
            {
                "fieldname": "custom_invoice_category",
                "label": "Invoice Category",
                "fieldtype": "Select",
                "options": "Regular\nCredit Note\nDebit Note\nProforma",
                "insert_after": "title",
                "default": "Regular",
                "description": "Classify the type of invoice"
            },
            {
                "fieldname": "custom_payment_terms_desc",
                "label": "Payment Terms Description",
                "fieldtype": "Text",
                "insert_after": "custom_invoice_category",
                "description": "Detailed payment terms for the customer"
            },
            {
                "fieldname": "custom_invoice_reference",
                "label": "Related Sales Order",
                "fieldtype": "Link",
                "options": "Sales Order",
                "insert_after": "custom_payment_terms_desc",
                "description": "Link to the original sales order"
            }
        ]
    }
    
    try:
        create_custom_fields(custom_fields, update=True)
        frappe.db.commit()
        print("Custom fields added to Sales Invoice")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        frappe.log_error(frappe.get_traceback(), "Patch Error: add_sales_invoice_custom_fields_003")
        raise

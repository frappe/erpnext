"""
Patch: Add custom fields to Purchase Order
Version: v17
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Add custom fields to Purchase Order"""
    
    print("\nRunning Patch: Add Purchase Order Custom Fields (v17)")
    
    custom_fields = {
        "Purchase Order": [
            {
                "fieldname": "custom_po_category",
                "label": "PO Category",
                "fieldtype": "Select",
                "options": "Raw Materials\nConsumables\nServices\nCapital Equipment",
                "insert_after": "title",
                "description": "Categorize the type of purchase"
            },
            {
                "fieldname": "custom_budget_code",
                "label": "Budget Code",
                "fieldtype": "Link",
                "options": "Cost Center",
                "insert_after": "custom_po_category",
                "description": "Link to the cost center for budgeting"
            },
            {
                "fieldname": "custom_procurement_notes",
                "label": "Procurement Notes",
                "fieldtype": "Text Editor",
                "insert_after": "custom_budget_code",
                "description": "Special instructions for procurement"
            }
        ]
    }
    
    try:
        create_custom_fields(custom_fields, update=True)
        frappe.db.commit()
        print("Custom fields added to Purchase Order")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        frappe.log_error(frappe.get_traceback(), "Patch Error: add_purchase_order_custom_fields_002")
        raise

"""
Patch: Add custom fields to Sales Order
Version: v17
Author: Muhammad Saad Qureshi
Date: 2026-02-19
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Add custom fields to Sales Order"""
    
    print("\n" + "="*60)
    print("Running Patch: Add Sales Order Custom Fields (v17)")
    print("="*60)
    
    custom_fields = {
        "Sales Order": [
            {
                "fieldname": "custom_order_priority",
                "label": "Order Priority",
                "fieldtype": "Select",
                "options": "Low\nMedium\nHigh\nUrgent",
                "insert_after": "title",
                "default": "Medium",
                "description": "Set the priority level for this order"
            },
            {
                "fieldname": "custom_internal_notes",
                "label": "Internal Notes",
                "fieldtype": "Text Editor",
                "insert_after": "custom_order_priority",
                "description": "Add notes visible only to your team"
            },
            {
                "fieldname": "custom_approval_required",
                "label": "Requires Approval",
                "fieldtype": "Check",
                "insert_after": "custom_internal_notes",
                "default": 0,
                "description": "Check if this order needs approval before submission"
            },
            {
                "fieldname": "custom_approved_by",
                "label": "Approved By",
                "fieldtype": "Link",
                "options": "User",
                "insert_after": "custom_approval_required",
                "read_only": 1,
                "description": "User who approved this order"
            },
            {
                "fieldname": "custom_approval_date",
                "label": "Approval Date",
                "fieldtype": "DateTime",
                "insert_after": "custom_approved_by",
                "read_only": 1,
                "description": "Date and time of approval"
            }
        ]
    }
    
    try:
        create_custom_fields(custom_fields, update=True)
        frappe.db.commit()
        
        print("Custom fields created successfully")
        print("   - custom_order_priority")
        print("   - custom_internal_notes")
        print("   - custom_approval_required")
        print("   - custom_approved_by")
        print("   - custom_approval_date")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        frappe.log_error(frappe.get_traceback(), "Patch Error: add_sales_order_custom_fields_001")
        raise

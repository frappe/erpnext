import frappe
from frappe import _
from datetime import datetime, timedelta

def get_data():
	return {
		"fieldname": "purchase_invoice",
		"non_standard_fieldnames": {
			"Journal Entry": "reference_name",
			"Payment Entry": "reference_name",
			"Payment Request": "reference_name",
			"Landed Cost Voucher": "receipt_document",
			"Purchase Invoice": "return_against",
			"Auto Repeat": "reference_document",
		},
		"internal_links": {
			"Purchase Order": ["items", "purchase_order"],
			"Purchase Receipt": ["items", "purchase_receipt"],
		},
		"transactions": [
			{"label": _("Payment"), "items": ["Payment Entry", "Payment Request", "Journal Entry"]},
			{
				"label": _("Reference"),
				"items": ["Purchase Order", "Purchase Receipt", "Asset", "Landed Cost Voucher"],
			},
			{"label": _("Returns"), "items": ["Purchase Invoice"]},
			{"label": _("Subscription"), "items": ["Auto Repeat"]},
		],
	}

@frappe.whitelist()
def get_total_invoice_due():
    """Returns total outstanding amount for Accounts Payable (Purchase Invoices where status != 'Paid')"""
    total_due = frappe.db.sql("""
        SELECT SUM(outstanding_amount)
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1 AND outstanding_amount > 0
    """)[0][0] or 0

    return {
        "value": total_due,
        "fieldtype": "Currency",
        "route": ["query-report", "Accounts Payable"],
        "route_options": {
            "status": ["!=", "Paid"]
        }
    }
@frappe.whitelist()
def get_weekly_invoice_due():
    """Returns total outstanding amount for Accounts Payable (Purchase Invoices) in the current week"""
    today = datetime.today().date()
    start_of_week = today - timedelta(days=today.weekday())  
    end_of_week = start_of_week + timedelta(days=6)  

    total_due = frappe.db.sql("""
        SELECT SUM(outstanding_amount)
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1
        AND outstanding_amount > 0
        AND due_date BETWEEN %s AND %s
    """, (start_of_week, end_of_week))[0][0] or 0

    return {
        "value": total_due,
        "fieldtype": "Currency",
        "route": ["query-report", "Accounts Payable"],
        "route_options": {
            "company": frappe.defaults.get_user_default("Company"),
            "report_date": str(end_of_week), 
            "ageing_based_on": "Due Date",
            "calculate_ageing_with": "Report Date"
        }
    }


# 	@frappe.whitelist()
# def get_total_payments_due():
#     """Returns total outstanding amount for Purchase Invoices where status != 'Paid'"""
#     total_due = frappe.db.sql("""
#         SELECT SUM(outstanding_amount)
#         FROM `tabPurchase Invoice`
#         WHERE docstatus = 1 AND status != 'Paid'
#     """)[0][0] or 0

#     return {
#         "value": total_due,
#         "fieldtype": "Currency",
#         "route": ["List", "Purchase Invoice"],
#         "route_options": {
#             "status": ["!=", "Paid"]
#         }
#     }
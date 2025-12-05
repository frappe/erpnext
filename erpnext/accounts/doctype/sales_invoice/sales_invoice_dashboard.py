import frappe
from frappe import _
from datetime import datetime, timedelta

def get_data():
	return {
		"fieldname": "sales_invoice",
		"non_standard_fieldnames": {
			"Delivery Note": "against_sales_invoice",
			"Journal Entry": "reference_name",
			"Payment Entry": "reference_name",
			"Payment Request": "reference_name",
			"Sales Invoice": "return_against",
			"Auto Repeat": "reference_document",
			"Purchase Invoice": "inter_company_invoice_reference",
		},
		"internal_links": {
			"Sales Order": ["items", "sales_order"],
			"Timesheet": ["timesheets", "time_sheet"],
		},
		"internal_and_external_links": {
			"Delivery Note": ["items", "delivery_note"],
		},
		"transactions": [
			{
				"label": _("Payment"),
				"items": [
					"Payment Entry",
					"Payment Request",
					"Journal Entry",
					"Invoice Discounting",
					"Dunning",
				],
			},
			{"label": _("Reference"), "items": ["Timesheet", "Delivery Note", "Sales Order"]},
			{"label": _("Returns"), "items": ["Sales Invoice"]},
			{"label": _("Subscription"), "items": ["Auto Repeat"]},
			{"label": _("Internal Transfers"), "items": ["Purchase Invoice"]},
		],
	}


@frappe.whitelist()
def get_total_receivables_due():
    """Returns total outstanding amount for Sales Invoices where status != 'Paid'"""
    total_due = frappe.db.sql("""
        SELECT SUM(outstanding_amount)
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND status != 'Paid'
    """)[0][0] or 0

    return {
        "value": total_due,
        "fieldtype": "Currency",
        "route": ["List", "Sales Invoice"],
        "route_options": {
            "status": ["!=", "Paid"]
        }
    }


@frappe.whitelist()
def get_weekly_receivables_due():
    """Returns total outstanding amount for Sales Invoices where status != 'Paid' in the current week"""
    today = datetime.today().date()
    start_of_week = today - timedelta(days=today.weekday())  
    end_of_week = start_of_week + timedelta(days=6)  
    total_due = frappe.db.sql("""
        SELECT SUM(outstanding_amount)
        FROM `tabSales Invoice`
        WHERE docstatus = 1
        AND status != 'Paid'
        AND due_date BETWEEN %s AND %s
    """, (start_of_week, end_of_week))[0][0] or 0

    return {
        "value": total_due,
        "fieldtype": "Currency",
        "route": ["List", "Sales Invoice"],
        "route_options": {
            "status": ["!=", "Paid"],
            "due_date": ["between", [str(start_of_week), str(end_of_week)]]
        }
    }
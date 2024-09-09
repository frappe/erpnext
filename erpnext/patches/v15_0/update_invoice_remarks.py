import frappe
from frappe import _


def execute():
	update_sales_invoice_remarks()
	update_purchase_invoice_remarks()


def update_sales_invoice_remarks():
	si_list = frappe.db.get_all(
		"Sales Invoice",
		filters={
			"docstatus": 1,
			"remarks": "No Remarks",
			"po_no": ["!=", ""],
		},
		fields=["name", "po_no"],
	)

	for doc in si_list:
		remarks = _("Against Customer Order {0}").format(doc.po_no)
		update_remarks("Sales Invoice", doc.name, remarks)


def update_purchase_invoice_remarks():
	pi_list = frappe.db.get_all(
		"Purchase Invoice",
		filters={
			"docstatus": 1,
			"remarks": "No Remarks",
			"bill_no": ["!=", ""],
		},
		fields=["name", "bill_no"],
	)

	for doc in pi_list:
		remarks = _("Against Supplier Invoice {0}").format(doc.bill_no)
		update_remarks("Purchase Invoice", doc.name, remarks)


def update_remarks(doctype, docname, remarks):
	filters = {
		"voucher_type": doctype,
		"remarks": "No Remarks",
		"voucher_no": docname,
	}

	frappe.db.set_value(doctype, docname, "remarks", remarks)
	frappe.db.set_value("GL Entry", filters, "remarks", remarks)
	frappe.db.set_value("Payment Ledger Entry", filters, "remarks", remarks)

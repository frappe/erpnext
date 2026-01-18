import frappe
from frappe.query_builder import DocType


def execute():
	POSInvoice = DocType("POS Invoice")

	frappe.qb.update(POSInvoice).set(POSInvoice.status, "Cancelled").where(POSInvoice.docstatus == 2).run()

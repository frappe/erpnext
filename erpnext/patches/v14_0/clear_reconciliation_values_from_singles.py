import frappe
from frappe import qb


def execute():
	"""
	Clear `tabSingles` and Payment Reconciliation tables of values
	"""
	singles = qb.DocType("Singles")
	qb.from_(singles).delete().where(singles.doctype == "Payment Reconciliation").run()
	doctypes = [
		"Payment Reconciliation Invoice",
		"Payment Reconciliation Payment",
		"Payment Reconciliation Allocation",
	]
	for x in doctypes:
		# child tables may not exist yet on sites where this pre-model-sync patch runs first
		if not frappe.db.table_exists(x):
			continue
		dt = qb.DocType(x)
		qb.from_(dt).delete().run()

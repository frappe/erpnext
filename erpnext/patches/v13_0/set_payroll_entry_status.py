import frappe
from frappe.query_builder import Case


def execute():
	PayrollEntry = frappe.qb.DocType("Payroll Entry")

	(
		frappe.qb.update(PayrollEntry).set(
			"status",
			Case()
			.when(PayrollEntry.docstatus == 0, "Draft")
			.when(PayrollEntry.docstatus == 1, "Submitted")
			.else_("Cancelled"),
		)
	).run()

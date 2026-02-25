import frappe


def execute():
	frappe.db.sql(
		""" UPDATE `tabQuotation` set status = 'Open'
		where docstatus = 1 and status = 'Submitted' """
	)

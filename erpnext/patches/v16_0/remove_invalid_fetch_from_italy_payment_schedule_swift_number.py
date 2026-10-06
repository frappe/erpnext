import frappe


def execute():
	"""Italy: `Payment Schedule.bank_account_swift_number` fetched `bank_account.swift_number`,
	a field that does not exist on Bank Account, so saving any document with a Payment Schedule
	bank account failed with "Unknown column 'swift_number'". The value is now set in
	`erpnext.regional.italy.utils.set_payment_schedule_swift_number`."""
	filters = {"dt": "Payment Schedule", "fieldname": "bank_account_swift_number"}
	if frappe.db.get_value("Custom Field", filters, "fetch_from") != "bank_account.swift_number":
		return

	frappe.db.set_value("Custom Field", filters, "fetch_from", None)
	frappe.clear_cache(doctype="Payment Schedule")

import frappe


def execute():
	if frappe.db.get_value("Journal Entry Account", {"reference_due_date": ""}):
		frappe.db.sql(
			"""
			UPDATE `tabJournal Entry Account`
			SET reference_due_date = NULL
			WHERE reference_due_date = ''
		"""
		)

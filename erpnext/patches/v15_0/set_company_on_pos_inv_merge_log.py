import frappe


def execute():
	pos_invoice_merge_logs = frappe.db.get_all(
		"POS Invoice Merge Log", {"docstatus": 1}, ["name", "pos_closing_entry"]
	)

	frappe.db.auto_commit_on_many_writes = 1
	for log in pos_invoice_merge_logs:
		if log.pos_closing_entry and frappe.db.exists("POS Closing Entry", log.pos_closing_entry):
			company = frappe.db.get_value("POS Closing Entry", log.pos_closing_entry, "company")
			frappe.db.set_value("POS Invoice Merge Log", log.name, "company", company)

	frappe.db.auto_commit_on_many_writes = 0

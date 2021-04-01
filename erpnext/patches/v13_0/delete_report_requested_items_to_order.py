import frappe

def execute():
	""" Check for one or multiple Auto Email Reports and delete """
	auto_email_reports = frappe.db.get_values("Auto Email Report", {"report": "Requested Items to Order"}, ["name"])
	for auto_email_report in auto_email_reports:
		frappe.delete_doc("Auto Email Report", auto_email_report[0])

	frappe.db.sql("""
		DELETE FROM `tabReport`
		WHERE name = 'Requested Items to Order'
	""")
import frappe

def execute():
	if frappe.db.table_exists("Time Log"):
		frappe.db.sql("""delete from `tabDocType`
			where name in('Time Log Batch', 'Time Log Batch Detail', 'Time Log')""")

	report = "Daily Time Log Summary"
	if frappe.db.exists("Report", report):
		frappe.delete_doc('Report', report)
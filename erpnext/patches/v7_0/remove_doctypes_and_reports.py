import frappe

def execute():
	if frappe.db.table_exists("Time Log"):
		frappe.db.sql("""delete from `tabDocType`
			where name in('Time Log Batch', 'Time Log Batch Detail', 'Time Log')""")

	frappe.db.sql("""delete from `tabDocField` where parent in ('Time Log', 'Time Log Batch')""")
	frappe.db.sql("""update `tabCustom Script` set dt = 'Timesheet' where dt = 'Time Log'""")

	for data in frappe.db.sql(""" select label, fieldname from  `tabCustom Field` where dt = 'Time Log'""", as_dict=1):
		custom_field = frappe.get_doc({
			'doctype': 'Custom Field',
			'label': data.label,
			'dt': 'Timesheet Detail',
			'fieldname': data.fieldname,
			'fieldtype': data.fieldtype or "Data"
		}).insert(ignore_permissions=True)

	frappe.db.sql("""delete from `tabCustom Field` where dt = 'Time Log'""")
	frappe.reload_doc('projects', 'doctype', 'timesheet')
	frappe.reload_doc('projects', 'doctype', 'timesheet_detail')

	report = "Daily Time Log Summary"
	if frappe.db.exists("Report", report):
		frappe.delete_doc('Report', report)

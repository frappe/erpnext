import frappe

def execute():
	if frappe.db.table_exists("Time Sheet") and not frappe.db.table_exists("Timesheet"):
		frappe.rename_doc("DocType", "Time Sheet", "Timesheet")
		frappe.rename_doc("DocType", "Time Sheet Detail", "Timesheet Detail")
		
		for doctype in ['Time Sheet', 'Time Sheet Detail']:
			frappe.delete_doc('DocType', doctype)
		
		report = "Daily Time Sheet Summary"
		if frappe.db.exists("Report", report):
			frappe.delete_doc('Report', report)

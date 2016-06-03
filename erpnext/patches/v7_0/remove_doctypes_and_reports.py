import frappe

def execute():
	for doctype in ['Time Log Batch', 'Time Log Batch Detail', 'Time Log']:
		frappe.delete_doc('DocType', doctype)
		
	report = "Daily Time Log Summary"
	if frappe.db.exists("Report", report):
		frappe.delete_doc('Report', report)
import frappe

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		if frappe.db.exists("DocType", "GST Settings"):
			frappe.delete_doc("DocType", "GST Settings")
			frappe.delete_doc("DocType", "GST HSN Code")
		
			for report_name in ('GST Sales Register', 'GST Purchase Register',
				'GST Itemised Sales Register', 'GST Itemised Purchase Register'):

				frappe.delete_doc('Report', report_name)
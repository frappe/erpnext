import frappe

def execute():
	frappe.reload_doc('regional', 'doctype', 'gst_hsn_code')

	for report_name in ('GST Sales Register', 'GST Purchase Register',
		'GST Itemised Sales Register', 'GST Itemised Purchase Register'):

		frappe.reload_doc('regional', 'report', frappe.scrub(report_name))

	if frappe.db.get_single_value('System Settings', 'country')=='India':
		from erpnext.regional.india.setup import setup
		setup()

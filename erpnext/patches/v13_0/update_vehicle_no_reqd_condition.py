import frappe


def execute():
	frappe.reload_doc('custom', 'doctype', 'custom_field', force=True)
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	if frappe.db.exists('Custom Field', { 'fieldname': 'vehicle_no' }):
		frappe.db.set_value('Custom Field', { 'fieldname': 'vehicle_no' }, 'mandatory_depends_on', '')

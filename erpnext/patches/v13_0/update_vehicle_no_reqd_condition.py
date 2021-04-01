import frappe

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	if frappe.db.exists('Custom Field', { 'fieldname': 'vehicle_no' }):
		if frappe.db.field_exists('Custom Field', 'mandatory_depends_on'):
			frappe.db.set_value('Custom Field', { 'fieldname': 'vehicle_no' }, 'mandatory_depends_on', '')

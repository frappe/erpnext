import frappe
from frappe.permissions import add_permission, update_permission_property

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	for doctype in ('GST HSN Code', 'GST Settings'):
		add_permission(doctype, 'Accounts Manager', 0)
		update_permission_property(doctype, 'Accounts Manager', 0, 'write', 1)
		update_permission_property(doctype, 'Accounts Manager', 0, 'create', 1)
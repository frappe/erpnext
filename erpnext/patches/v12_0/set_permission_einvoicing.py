import frappe
from frappe.permissions import add_permission, update_permission_property

def execute():
	company = frappe.get_all('Company', filters = {'country': 'Italy'})

	if not company:
		return

	add_permission('Import Supplier Invoice', 'Accounts Manager', 0)
	update_permission_property('Import Supplier Invoice', 'Accounts Manager', 0, 'write', 1)
	update_permission_property('Import Supplier Invoice', 'Accounts Manager', 0, 'create', 1)
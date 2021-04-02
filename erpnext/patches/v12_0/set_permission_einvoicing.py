import frappe
from erpnext.regional.italy.setup import make_custom_fields
from frappe.permissions import add_permission, update_permission_property

def execute():
	company = frappe.get_all('Company', filters = {'country': 'Italy'})

	if not company:
		return

	make_custom_fields()

	frappe.reload_doc("regional", "doctype", "import_supplier_invoice")

	add_permission('Import Supplier Invoice', 'Accounts Manager', 0)
	update_permission_property('Import Supplier Invoice', 'Accounts Manager', 0, 'write', 1)
	update_permission_property('Import Supplier Invoice', 'Accounts Manager', 0, 'create', 1)

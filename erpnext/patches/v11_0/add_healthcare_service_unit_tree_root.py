import frappe
from frappe import _

def execute():
	""" assign lft and rgt appropriately """
	frappe.reload_doc("healthcare", "doctype", "healthcare_service_unit")
	frappe.reload_doc("healthcare", "doctype", "healthcare_service_unit_type")

	if not frappe.db.exists("Healthcare Service Unit", _('All Healthcare Service Units')):
		frappe.get_doc({
			'doctype': 'Healthcare Service Unit',
			'healthcare_service_unit_name': _('All Healthcare Service Units'),
			'is_group': 1
		}).insert(ignore_permissions=True)

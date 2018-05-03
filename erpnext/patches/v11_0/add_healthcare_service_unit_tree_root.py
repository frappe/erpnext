import frappe
from frappe import _
from frappe.utils.nestedset import rebuild_tree

def execute():
	""" assign lft and rgt appropriately """
	frappe.reload_doc("healthcare", "doctype", "healthcare_service_unit")

	if not frappe.db.exists("Healthcare Service Unit", _('All Healthcare Service Unit')):
		frappe.get_doc({
			'doctype': 'Healthcare Service Unit',
			'healthcare_service_unit_name': _('All Healthcare Service Unit'),
			'is_group': 1
		}).insert(ignore_permissions=True)

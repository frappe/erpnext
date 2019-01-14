import frappe
from frappe import _

def execute():
	quality_management_module_icons = frappe.get_all('Desktop Icon', filters={
		'module_name': 'Quality Management'
	}, fields=['name'])

	for icon in quality_management_module_icons:
		frappe.db.set_value('Desktop Icon', icon.name, 'label', _('Quality'))
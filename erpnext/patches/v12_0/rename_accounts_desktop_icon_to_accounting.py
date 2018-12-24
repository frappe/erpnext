import frappe
from frappe import _

def execcute():
	accounts_module_icons = frappe.get_all('Desktop Icon', filters={
		'module_name': 'Accounts'
	}, fields=['name'])

	for icon in accounts_module_icons:
		frappe.db.set_value('Desktop Icon', icon.name, 'label', _('Accounting'))
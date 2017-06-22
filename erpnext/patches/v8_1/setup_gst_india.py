import frappe

def execute():
	if frappe.db.get_single_value('System Settings', 'country')=='India':
		from erpnext.regional.india.setup import setup
		setup()

import frappe
from erpnext.regional.india.setup import add_permissions

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	add_permissions()
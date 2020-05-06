import frappe
from erpnext.regional.india.setup import add_permissions

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	frappe.reload_doc("regional", "doctype", "lower_deduction_certificate")
	frappe.reload_doc("regional", "doctype", "gstr_3b_report")
	add_permissions()

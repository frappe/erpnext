import frappe
from erpnext.regional.india.setup  import make_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	frappe.reload_doc('hr', 'doctype', 'Employee Tax Exemption Declaration')
	frappe.reload_doc('hr', 'doctype', 'Employee Tax Exemption Proof Submission')
	make_custom_fields()
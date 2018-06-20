import frappe
from erpnext.regional.india.setup  import make_custom_fields

def execute():
	frappe.reload_doc('hr', 'doctype', 'employee_tax_exemption_proof_submission')
	frappe.reload_doc('hr', 'doctype', 'employee_tax_exemption_declaration')
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	make_custom_fields()
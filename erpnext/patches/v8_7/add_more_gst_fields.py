import frappe
from erpnext.regional.india.setup  import make_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	frappe.reload_doc('hr', 'doctype', 'employee_tax_exemption_declaration')
	frappe.reload_doc('hr', 'doctype', 'employee_tax_exemption_proof_submission')
	make_custom_fields()
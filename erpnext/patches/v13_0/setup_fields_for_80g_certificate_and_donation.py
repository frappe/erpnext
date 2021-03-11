import frappe
from erpnext.regional.india.setup import make_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	make_custom_fields()

	if not frappe.db.exists('Party Type', 'Donor'):
		frappe.get_doc({
			'doctype': 'Party Type',
			'party_type': 'Donor',
			'account_type': 'Receivable'
		}).insert(ignore_permissions=True)
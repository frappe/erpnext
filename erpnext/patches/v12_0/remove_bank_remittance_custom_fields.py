from __future__ import unicode_literals
import frappe
from erpnext.regional.india.setup import make_custom_fields

def execute():
	frappe.reload_doc("accounts", "doctype", "tax_category")
	frappe.reload_doc("stock", "doctype", "item_manufacturer")
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return
	if frappe.db.exists("Custom Field", "Company-bank_remittance_section"):
		deprecated_fields = ['bank_remittance_section', 'client_code', 'remittance_column_break', 'product_code']
		for i in range(len(deprecated_fields)):
			frappe.delete_doc("Custom Field", 'Company-'+deprecated_fields[i])
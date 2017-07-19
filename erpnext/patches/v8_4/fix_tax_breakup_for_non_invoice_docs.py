import frappe
from erpnext.regional.india.setup import make_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	make_custom_fields()
	
	# update invoice copy value
	values = ["Original for Recipient", "Duplicate for Transporter", 
		"Duplicate for Supplier", "Triplicate for Supplier"]
	for d in values:
		frappe.db.sql("update `tabSales Invoice` set invoice_copy=%s where invoice_copy=%s", (d, d))
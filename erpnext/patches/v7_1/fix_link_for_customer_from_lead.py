import frappe

def execute():
	for c in frappe.db.sql('select name from tabCustomer where ifnull(lead_name,"")!=""'):
		customer = frappe.get_doc('Customer', c[0])
		customer.update_lead_status()
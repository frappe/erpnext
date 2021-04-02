from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype('System Settings')
	companies = frappe.db.sql("""select name, country
		from tabCompany order by creation asc""", as_dict=True)
	if companies:
		frappe.db.set_value('System Settings', 'System Settings', 'setup_complete', 1)

	for company in companies:
		if company.country:
			frappe.db.set_value('System Settings', 'System Settings', 'country', company.country)
			break



from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('setup','doctype','sales_person')
	frappe.db.sql("""update `tabSales Person` set enabled=1 
		where (employee is null or employee = '' 
			or employee IN (select employee from tabEmployee where status != "Left"))""")

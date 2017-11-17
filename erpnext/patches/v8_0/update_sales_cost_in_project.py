from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql("""
		update `tabProject` p
		set total_sales_cost = ifnull((select sum(base_grand_total)
			from `tabSales Order` where project=p.name and docstatus=1), 0)
	""")
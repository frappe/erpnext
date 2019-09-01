from __future__ import unicode_literals
import frappe, os
from frappe import _

def execute():
	frappe.reload_doc("stock", "doctype", "item_price")
	frappe.db.sql("""
		update `tabItem Price` p
		inner join `tabItem` i on i.name = p.item_code
		set
			p.item_name = i.item_name,
			p.item_description = i.description,
			p.item_group = i.item_group,
			p.brand = i.brand
	""")
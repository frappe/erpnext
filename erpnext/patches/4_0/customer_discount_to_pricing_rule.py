# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "pricing_rule")
	
	frappe.db.auto_commit_on_many_writes = True
	
	for d in frappe.db.sql("""select * from `tabCustomer Discount` 
		where ifnull(parent, '') != '' and docstatus < 2""", as_dict=1):
			if not d.item_group:
				item_group = frappe.db.sql("""select name from `tabItem Group` 
					where ifnull(parent_item_group, '') = ''""")[0][0]
			else:
				item_group = d.item_group
				
			frappe.get_doc([{
				"doctype": "Pricing Rule",
				"apply_on": "Item Group",
				"item_group": item_group,
				"applicable_for": "Customer",
				"customer": d.parent,
				"price_or_discount": "Discount",
				"discount_percentage": d.discount
			}]).insert()
	
	frappe.db.auto_commit_on_many_writes = False		
	
	frappe.delete_doc("DocType", "Customer Discount")
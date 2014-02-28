# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "pricing_rule")
	
	for d in frappe.db.sql("""select * from `tabCustomer Discount` 
		where ifnull(parent, '') != '' and docstatus < 2""", as_dict=1):
			frappe.bean([{
				"doctype": "Pricing Rule",
				"apply_on": "Item Group",
				"item_group": d.item_group,
				"applicable_for": "Customer",
				"customer": d.parent,
				"price_or_discount": "Discount",
				"discount_percentage": d.discount
			}]).insert()
			
	
	frappe.delete_doc("DocType", "Customer Discount")
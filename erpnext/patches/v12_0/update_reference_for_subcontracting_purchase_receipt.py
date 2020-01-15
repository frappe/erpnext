# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from six import iteritems
from erpnext.controllers.buying_controller import get_subcontracted_raw_materials_from_se

def execute():
	frappe.reload_doc("stock", "doctype", "purchase_receipt")
	frappe.reload_doc("stock", "doctype", "purchase_receipt_item")
	frappe.reload_doc("buying", "doctype", "purchase_receipt_item_supplied")

	purchase_receipts = frappe.db.sql(""" SELECT distinct `tabPurchase Receipt`.name
		FROM 
			`tabPurchase Receipt`, `tabPurchase Receipt Item Supplied`
		WHERE
			`tabPurchase Receipt Item Supplied`.parent = `tabPurchase Receipt`.name 
			AND (`tabPurchase Receipt Item Supplied`.reference_name is null 
				OR `tabPurchase Receipt Item Supplied`.reference_name = '')
			AND `tabPurchase Receipt`.docstatus = 1
			AND `tabPurchase Receipt`.is_subcontracted = 'Yes' """, as_dict=1)

	for purchase_receipt in purchase_receipts:
		pr_doc = frappe.get_doc("Purchase Receipt", purchase_receipt.name)

		for item in pr_doc.items:
			#Get transferred materials against the purchase order
			raw_materials = get_subcontracted_raw_materials_from_se(item.purchase_order,
				item.purchase_order_item, item.item_code)

			total_count = len(raw_materials)
			for data in raw_materials:
				for supplied_item in pr_doc.supplied_items:
					if (total_count > 0 and data.main_item_code == supplied_item.main_item_code
						and data.rm_item_code == supplied_item.rm_item_code
						and not supplied_item.reference_name):
						supplied_item.reference_name = item.name
						total_count -= 1
						supplied_item.db_set("reference_name", item.name)
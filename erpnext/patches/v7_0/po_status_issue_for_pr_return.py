# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	parent_list = []
	count = 0
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt')

	for data in frappe.db.sql("""
		select
			`tabPurchase Receipt Item`.purchase_order, `tabPurchase Receipt Item`.name,
			`tabPurchase Receipt Item`.item_code, `tabPurchase Receipt Item`.idx,
			`tabPurchase Receipt Item`.parent
		from
			`tabPurchase Receipt Item`, `tabPurchase Receipt`
		where
			`tabPurchase Receipt Item`.parent = `tabPurchase Receipt`.name and
			`tabPurchase Receipt Item`.purchase_order_item is null and
			`tabPurchase Receipt Item`.purchase_order is not null and
			`tabPurchase Receipt`.is_return = 1""", as_dict=1):
			name = frappe.db.get_value('Purchase Order Item',
				{'item_code': data.item_code, 'parent': data.purchase_order, 'idx': data.idx}, 'name')

			if name:
				frappe.db.set_value('Purchase Receipt Item', data.name, 'purchase_order_item', name, update_modified=False)
				parent_list.append(data.parent)

			count +=1
			if count % 200 == 0:
				frappe.db.commit()

	if len(parent_list) > 0:
		for parent in set(parent_list):
			doc = frappe.get_doc('Purchase Receipt', parent)
			doc.update_qty(update_modified=False)
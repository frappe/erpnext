# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('stock', 'doctype', 'item')
	frappe.db.sql(""" update `tabItem` set allow_transfer_for_manufacture = 1
		where ifnull(is_stock_item, 0) = 1""")

	for doctype in ['BOM Item', 'Work Order Item', 'BOM Explosion Item']:
		frappe.reload_doc('manufacturing', 'doctype', frappe.scrub(doctype))

		frappe.db.sql(""" update `tab{0}` child, tabItem item
			set
				child.allow_transfer_for_manufacture = 1
			where
				child.item_code = item.name and ifnull(item.is_stock_item, 0) = 1
		""".format(doctype))
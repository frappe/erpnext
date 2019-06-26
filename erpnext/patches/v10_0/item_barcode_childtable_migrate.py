# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
	if frappe.get_all("Item Barcode", limit=1): return
	frappe.reload_doc("stock", "doctype", "item_barcode")

	items_barcode = frappe.db.sql("select name, barcode from tabItem where barcode is not null", as_dict=True)
	frappe.reload_doc("stock", "doctype", "item")



	for item in items_barcode:
		barcode = item.barcode.strip()

		if barcode and '<' not in barcode:
			try:
				frappe.get_doc({
					'idx': 0,
					'doctype': 'Item Barcode',
					'barcode': barcode,
					'parenttype': 'Item',
					'parent': item.name,
					'parentfield': 'barcodes'
				}).insert()
			except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
				continue

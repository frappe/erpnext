# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "item_barcode")
	if frappe.get_all("Item Barcode", limit=1):
		return
	if "barcode" not in frappe.db.get_table_columns("Item"):
		return

	items_barcode = frappe.get_all("Item", filters={"barcode": ["is", "set"]}, fields=["name", "barcode"])
	frappe.reload_doc("stock", "doctype", "item")

	for item in items_barcode:
		barcode = item.barcode.strip()

		if barcode and "<" not in barcode:
			try:
				frappe.get_doc(
					{
						"idx": 0,
						"doctype": "Item Barcode",
						"barcode": barcode,
						"parenttype": "Item",
						"parent": item.name,
						"parentfield": "barcodes",
					}
				).insert()
			except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
				continue

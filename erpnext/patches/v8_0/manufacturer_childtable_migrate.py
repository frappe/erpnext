# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():

	# reading from json and writing it to mariadb
	# reload_doc needed here with information because new table introduced
	frappe.reload_doc('stock', 'doctype', 'item_manufacturer')
	# reload_doctype is a simpler concept of reload_doc
	frappe.reload_doctype('Item')

	item_manufacturers = frappe.get_all("Item", fields=["name", "manufacturer", "manufacturer_part_no"])
	for item in item_manufacturers:
		if item.manufacturer or item.manufacturer_part_no:
			item_doc = frappe.get_doc("Item", item.name)
			item_doc.append("manufacturers", {
				"manufacturer": item.manufacturer,
				"manufacturer_part_no": item.manufacturer_part_no
			})
			
			item_doc.get("manufacturers")[0].db_update()
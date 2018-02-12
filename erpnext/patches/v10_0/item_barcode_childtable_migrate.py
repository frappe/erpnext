# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
	items_barcode = frappe.db.sql("""SELECT name, barcode FROM tabItem
		WHERE barcode IS NOT NULL and barcode != ''""", as_dict=1)

	frappe.reload_doc("stock", "doctype", "item")
	frappe.reload_doc("stock", "doctype", "item_barcode")

	for item in items_barcode:
		doc = frappe.get_doc("Item", item.get("name"))
		if item.get("barcode"):
			doc.append("barcodes", {"barcode": item.get("barcode")})
			doc.flags.ignore_validate = True
			doc.flags.ignore_mandatory = True
			doc.save()
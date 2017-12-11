# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
    items_barcode = frappe.db.sql("SELECT name, barcode FROM tabItem WHERE barcode IS NOT NULL", as_dict=1)

    for item in items_barcode:
        doc = frappe.get_doc("Item", item.name)
        doc.append("barcodes", {"barcode": item.get("barcode")})
        doc.save()

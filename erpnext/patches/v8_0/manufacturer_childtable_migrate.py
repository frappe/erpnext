# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
    item_manufacturers = frappe.get_all("Item", fields=["name", "manufacturer", "manufacturer_part_no"])
    for item in item_manufacturers:
        item_doc = frappe.get_doc("Item", item.name)
        item_doc.append("manufacturers", {
            "manufacturer": item.manufacturer,
            "manufacturer_part_no": item.manufacturer_part_no
        })
        item_doc.flags.ignore_validate = True
        item_doc.flags.ignore_mandatory = True
        item_doc.save()

# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from pprint import pprint

def execute():
    stock_entries = frappe.get_all("Stock Entry", filters={"stock_entry_type": "Send to Subcontractor", "docstatus": 1}, fields=["name","purchase_order"])
    se_name = list(map(lambda x: {k:v for k, v in x.items() if k == 'name'}, stock_entries ))
    se_name = ', '.join(map(str, [l['name'] for l in se_name if 'name' in l]))
    stock_entries_detail =frappe.get_all("Stock Entry Detail", filters=[
            ["parent", "in", se_name]
        ],
        fields=["parent", "item_code", "qty"])
    records = {}

    for entry in stock_entries:
        for details in stock_entries_detail:
            if details.parent == entry.name:
                details["Purchase_order"] = entry.purchase_order
                if entry.purchase_order not in records:
                    records[entry.purchase_order] = {}
                    records[entry.purchase_order][details.item_code] = details.qty
                else:
                    records[entry.purchase_order][details.item_code] = records[entry.purchase_order].get(details.item_code, 0) + details.qty

    for k,v in records.items():
        for key,value in v.items():
            frappe.db.sql("update `tabPurchase Order Item Supplied` set transfered_qty = %s where parent = %s and rm_item_code = %s", (value, k, key))
# Copyright (c) 2022, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.stock.doctype.delivery_note.delivery_note import update_billed_amount_based_on_so


def execute():
    dn_item = frappe.qb.DocType('Delivery Note Item')

    so_detail_list = (frappe.qb.from_(dn_item)
        .select(dn_item.so_detail)
        .where(
            (dn_item.so_detail.notnull()) &
            (dn_item.so_detail != '') &
            (dn_item.docstatus == 1) &
            (dn_item.returned_qty > 0)
    )).run()

    for so_detail in so_detail_list:
        update_billed_amount_based_on_so(so_detail[0], False)
# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from frappe.model.rename_doc import rename_doc, get_link_fields
from frappe.model.utils.rename_field import rename_field
import frappe

def execute():
    rename_doc('DocType', 'Production Order', 'Work Order', force=True)
    frappe.reload_doc('manufacturing', 'doctype', 'work_order')

    rename_doc('DocType', 'Production Order Item', 'Work Order Item', force=True)
    frappe.reload_doc('manufacturing', 'doctype', 'work_order_item')

    rename_doc('DocType', 'Production Order Operation', 'Work Order Operation', force=True)
    frappe.reload_doc('manufacturing', 'doctype', 'work_order_operation')

    frappe.reload_doc('projects', 'doctype', 'timesheet')
    frappe.reload_doc('stock', 'doctype', 'stock_entry')

    # fetch all linked fields
    old, new = 'Production Order', 'Work Order'
    link_fields = get_link_fields(old)
    link_fields.extend(get_link_fields(new))

    for d in link_fields:
        if d['parent'] not in [old, new]:
            rename_field(d['parent'], frappe.scrub(old), frappe.scrub(new))

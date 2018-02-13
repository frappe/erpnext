# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from frappe.model.rename_doc import rename_doc, get_link_fields, update_link_field_values
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
            frappe.db.sql(""" update `tab{0}` set {1}={2} """
                .format(d['parent'], frappe.scrub(new), frappe.scrub(old)))

    update_naming_series()

def update_naming_series():
    work_order = frappe.get_all('Work Order')

    for doc in work_order:
        if "PRO-" in doc.name:
            new_name = doc.name.replace('PRO-', 'WO-')
            frappe.rename_doc('Work Order', doc.name, new_name, ignore_permissions=True)

    naming = frappe.get_doc('Naming Series')
    naming.prefix = 'PRO-'
    naming.get_current() # fetch current count for 'PRO-'
    naming.prefix = 'WO-'
    naming.update_series_start() # Update the count

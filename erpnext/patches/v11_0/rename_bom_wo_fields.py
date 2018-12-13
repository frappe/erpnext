# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
    for doctype in ['BOM Explosion Item', 'BOM Item', 'Work Order Item', 'Item']:
        if frappe.db.has_column(doctype, 'allow_transfer_for_manufacture'):
            rename_field('BOM Item', "allow_transfer_for_manufacture", "include_item_in_manufacturing")

    for doctype in ['BOM', 'Work Order']:
        frappe.reload_doc('manufacturing', 'doctype', frappe.scrub(doctype))

        if frappe.db.has_column(doctype, 'transfer_material_against_job_card'):
            frappe.db.sql(""" UPDATE `tab%s`
                SET transfer_material_against = CASE WHEN
                    transfer_material_against_job_card = 1 then 'Job Card' Else 'Work Order' END
                WHERE docstatus < 2""" % (doctype))
        else:
            frappe.db.sql(""" UPDATE `tab%s`
                SET transfer_material_against = 'Work Order'
                WHERE docstatus < 2""" % (doctype))
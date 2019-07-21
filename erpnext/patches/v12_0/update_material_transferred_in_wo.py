# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import frappe

def execute():
    frappe.reload_doc("manufacturing", "doctype", "work_order")

    if frappe.db.has_column('Work Order', 'material_transferred_for_manufacturing'):
        frappe.db.sql(""" UPDATE `tabWork Order`
            SET material_transferred = (material_transferred_for_manufacturing / qty) * 100
            WHERE
                docstatus < 2 and material_transferred_for_manufacturing > 0
                and ifnull(material_transferred, 0) = 0 """)
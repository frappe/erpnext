from __future__ import unicode_literals

import frappe


def execute():
    frappe.reload_doc("manufacturing", "doctype", "workstation")

    frappe.db.sql(""" UPDATE `tabWorkstation`
        SET production_capacity = 1 """)

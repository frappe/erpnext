from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
    """ copy data from old fields to new """
    frappe.reload_doc("projects", "doctype", "project")

    if frappe.db.has_column('Project', 'total_sales_cost'):
        rename_field('Project', "total_sales_cost", "total_sales_amount")

    if frappe.db.has_column('Project', 'total_billing_amount'):
        rename_field('Project', "total_billing_amount", "total_billable_amount")
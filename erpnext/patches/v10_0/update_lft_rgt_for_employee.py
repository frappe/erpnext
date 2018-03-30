import frappe
from frappe.utils.nestedset import rebuild_tree

def execute():
    """ assign lft and rgt appropriately """
    frappe.reload_doc("hr", "doctype", "employee")

    rebuild_tree("Employee", "reports_to")
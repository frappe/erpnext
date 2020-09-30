import frappe
from frappe import _

def execute():
    frappe.reload_doctype("System Settings")
    settings = frappe.get_doc("System Settings")
    settings.app_name = _("ERPNext")
    settings.save()
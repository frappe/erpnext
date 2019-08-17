from __future__ import unicode_literals
import frappe
from erpnext.regional.india.setup import make_custom_fields

def execute():
    frappe.reload_doc("accounts", "doctype", "tax_category")
    frappe.reload_doc("stock", "doctype", "item_manufacturer")
    company = frappe.get_all('Company', filters = {'country': 'India'})
    if not company:
        return

    make_custom_fields()
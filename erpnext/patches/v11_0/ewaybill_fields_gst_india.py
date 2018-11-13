import frappe
from erpnext.regional.india.setup import make_custom_fields, add_custom_roles_for_reports

def execute():
    company = frappe.get_all('Company', filters = {'country': 'India'})
    if not company:
        return

    # add custom fields for eway and regional hr reports
    make_custom_fields()

    # add roles to HR reports
    add_custom_roles_for_reports()
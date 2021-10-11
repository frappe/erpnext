from __future__ import unicode_literals

import frappe

from erpnext.regional.india.setup import add_custom_roles_for_reports


def execute():
    company = frappe.get_all('Company', filters = {'country': 'India'})
    if not company:
        return

    add_custom_roles_for_reports()

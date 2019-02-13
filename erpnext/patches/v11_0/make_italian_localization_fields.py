# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from erpnext.regional.italy.setup import make_custom_fields, setup_report
import frappe

def execute():
    company = frappe.get_all('Company', filters = {'country': 'Italy'})
    if not company:
      return

    make_custom_fields()
    setup_report()

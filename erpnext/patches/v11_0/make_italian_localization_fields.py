# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from erpnext.regional.italy.setup import make_custom_fields, setup_report
from erpnext.regional.italy import state_codes
import frappe


def execute():

    company = frappe.get_all('Company', filters = {'country': 'Italy'})
    if not company:
      return

    make_custom_fields()
    setup_report()

    # Set state codes
    condition = ""
    for state, code in state_codes.items():
      condition += " when '{0}' then '{1}'".format(frappe.db.escape(state), frappe.db.escape(code))

    if condition:
      frappe.db.sql("""
        UPDATE tabAddress set state_code = (case state {condition} end)
        WHERE country in ('Italy', 'Italia', 'Italian Republic', 'Repubblica Italiana')
      """.format(condition=condition))

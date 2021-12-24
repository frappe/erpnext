# Copyright (c) 2021, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.model import data_field_options


def execute():

    for field in frappe.get_all('Custom Field',
                            fields = ['name'],
                            filters = {
                                'fieldtype': 'Data',
                                'options': ['!=', None]
                            }):

        if field not in data_field_options:
            frappe.db.sql("""
                UPDATE
                    `tabCustom Field`
                SET
                    options=NULL
                WHERE
                    name=%s
            """, (field))

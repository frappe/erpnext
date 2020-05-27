# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
    frappe.db.sql("""UPDATE `tabPrint Format`
        SET module = 'Payroll'
        WHERE name IN ('Salary Slip Based On Timesheet', 'Salary Slip Standard')"""
    )
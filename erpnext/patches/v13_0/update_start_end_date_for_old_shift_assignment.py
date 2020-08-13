# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
    frappe.reload_doc('hr', 'doctype', 'shift_assignment')
    frappe.db.sql("update `tabShift Assignment` set end_date=date, start_date=date, status='Inactive'  where date IS NOT NULL and start_date IS NULL and end_date IS NULL;")
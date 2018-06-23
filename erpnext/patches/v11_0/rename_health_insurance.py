# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from frappe.model.rename_doc import rename_doc
import frappe

def execute():
	rename_doc('DocType', 'Health Insurance', 'Employee Health Insurance', force=True)
	frappe.reload_doc('hr', 'doctype', 'employee_health_insurance')
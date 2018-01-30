# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.setup.install import leave_application_workflow

def execute():
	frappe.reload_doc("hr", "doctype", "leave_application")
	frappe.reload_doc("workflow", "doctype", "workflow")
	leave_application_workflow()
	if frappe.db.has_column("Leave Application", "status"):
		frappe.db.sql("""update `tabLeave Application` set workflow_state = status""")

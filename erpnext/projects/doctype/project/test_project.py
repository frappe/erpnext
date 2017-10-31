# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe
test_records = frappe.get_test_records('Project')
test_ignore = ["Sales Order"]


def create_project():
	if not frappe.db.exists("Project", "_Test Project"):
		project = frappe.get_doc({
			"doctype":"Project",
			"project_name": "_Test Project",
			"status": "Open",
		})
		project.insert()

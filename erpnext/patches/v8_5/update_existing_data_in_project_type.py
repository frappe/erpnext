# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("projects", "doctype", "project_type")
	frappe.reload_doc("projects", "doctype", "project")

	project_types = ["Internal", "External", "Other"]

	for project_type in project_types:
		if not frappe.db.exists("Project Type", project_type):
			p_type = frappe.get_doc({
				"doctype": "Project Type",
				"project_type": project_type
			})
			p_type.insert()
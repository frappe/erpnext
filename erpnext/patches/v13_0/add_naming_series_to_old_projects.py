from __future__ import unicode_literals

import frappe


def execute():
	frappe.reload_doc("projects", "doctype", "project")

	frappe.db.sql("""UPDATE `tabProject`
		SET
			naming_series = 'PROJ-.####'
		WHERE
			naming_series is NULL""")

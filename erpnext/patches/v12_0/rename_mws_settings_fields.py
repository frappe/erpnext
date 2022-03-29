# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	count = frappe.db.sql(
		"SELECT COUNT(*) FROM `tabSingles` WHERE doctype='Amazon MWS Settings' AND field='enable_sync';"
	)[0][0]
	if count == 0:
		frappe.db.sql(
			"UPDATE `tabSingles` SET field='enable_sync' WHERE doctype='Amazon MWS Settings' AND field='enable_synch';"
		)

	frappe.reload_doc("ERPNext Integrations", "doctype", "Amazon MWS Settings")

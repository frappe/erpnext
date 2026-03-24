# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	if frappe.db.exists("Company", {"country": "India"}):
		return

	frappe.reload_doc("core", "doctype", "has_role")
	frappe.db.delete(
		"Has Role",
		{
			"parenttype": "Report",
			"parent": [
				"in",
				[
					"GST Sales Register",
					"GST Purchase Register",
					"GST Itemised Sales Register",
					"GST Itemised Purchase Register",
					"Eway Bill",
				],
			],
		},
	)

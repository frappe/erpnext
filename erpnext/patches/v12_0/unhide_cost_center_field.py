# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.db.delete(
		"Property Setter",
		{
			"doc_type": ["in", ["Sales Invoice", "Purchase Invoice", "Payment Entry"]],
			"field_name": "cost_center",
			"property": "hidden",
		},
	)

# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	"""Move from due_advance_amount to pending_amount"""

	if frappe.db.has_column("Employee Advance", "due_advance_amount"):
		frappe.db.sql(""" UPDATE `tabEmployee Advance` SET pending_amount=due_advance_amount """)

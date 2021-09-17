# Copyright (c) 2021, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	frappe.db.sql("""
		UPDATE `tabProduction Plan`
		SET status="Completed"
		WHERE total_produced_qty >= total_planned_qty
	""")

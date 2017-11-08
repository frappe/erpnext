# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("schools", "doctype", "fees")

	if "total_amount" not in frappe.db.get_table_columns("Fees"):
		return

	frappe.db.sql("""update tabFees set grand_total=total_amount where grand_total = 0.0""")
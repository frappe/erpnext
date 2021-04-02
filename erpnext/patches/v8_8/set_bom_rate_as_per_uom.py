# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql("""
		update `tabBOM Item`
		set rate = rate * conversion_factor
		where uom != stock_uom and docstatus < 2
			and conversion_factor not in (0, 1)
	""")
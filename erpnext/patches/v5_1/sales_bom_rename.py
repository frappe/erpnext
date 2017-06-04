# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	tables = frappe.db.sql_list("show tables")
	for old_dt, new_dt in [["Sales BOM Item", "Product Bundle Item"],
		["Sales BOM", "Product Bundle"]]:
			if "tab"+new_dt not in tables:
				frappe.rename_doc("DocType", old_dt, new_dt, force=True)

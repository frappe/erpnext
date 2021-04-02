# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.permissions

def execute():
	if "opn_description" in frappe.db.get_table_columns("BOM Operation"):
		frappe.db.sql("""update `tabBOM Operation` set description = opn_description
			where ifnull(description, '') = ''""")
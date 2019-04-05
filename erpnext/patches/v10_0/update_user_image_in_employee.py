# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('hr', 'doctype', 'employee')

	frappe.db.sql("""
		UPDATE
			`tabEmployee`, `tabUser`
		SET
			`tabEmployee`.image = `tabUser`.user_image
		WHERE
			`tabEmployee`.user_id = `tabUser`.name and
			`tabEmployee`.user_id is not null and
			`tabEmployee`.user_id != '' and `tabEmployee`.image is null
	""")

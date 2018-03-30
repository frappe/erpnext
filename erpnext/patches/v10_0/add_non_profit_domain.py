# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	domain = 'Non Profit'
	if not frappe.db.exists('Domain', domain):
		frappe.get_doc({
			'doctype': 'Domain',
			'domain': domain
		}).insert(ignore_permissions=True)

		frappe.get_doc({
			'doctype': 'Role',
			'role_name': 'Non Profit Portal User',
			'desk_access': 0,
			'restrict_to_domain': domain
		}).insert(ignore_permissions=True)
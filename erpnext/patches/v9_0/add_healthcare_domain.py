# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	domain = 'Healthcare'
	if not frappe.db.exists('Domain', domain):
		frappe.get_doc({
			'doctype': 'Domain',
			'domain': domain
		}).insert(ignore_permissions=True)
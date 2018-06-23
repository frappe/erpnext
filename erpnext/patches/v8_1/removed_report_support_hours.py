# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql(""" update `tabAuto Email Report` set report = %s
		where name = %s""", ('Support Hour Distribution', 'Support Hours'))

	frappe.db.sql(""" update `tabCustom Role` set report = %s
		where report = %s""", ('Support Hour Distribution', 'Support Hours'))

	frappe.delete_doc('Report', 'Support Hours')
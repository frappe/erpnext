# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype('Timesheet')
	company = frappe.get_all('Company')

	#Check more than one company exists
	if len(company) > 1:
		frappe.db.sql(""" update `tabTimesheet` set `tabTimesheet`.company =
			(select company from `tabProduction Order` where name = `tabTimesheet`.production_order)
			where production_order is not null and production_order !=''""")
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	country = frappe.db.get_single_value("Global Defaults", "country")
	if not country:
		print "Country not specified in Global Defaults"
		return

	for organization in frappe.db.sql_list("""select name from `tabOrganization`
		where ifnull(country, '')=''"""):
		frappe.db.set_value("Organization", organization, "country", country)

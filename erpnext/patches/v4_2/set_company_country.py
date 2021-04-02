# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import print_function, unicode_literals
import frappe

def execute():
	country = frappe.db.get_single_value("Global Defaults", "country")
	if not country:
		print("Country not specified in Global Defaults")
		return

	for company in frappe.db.sql_list("""select name from `tabCompany`
		where ifnull(country, '')=''"""):
		frappe.db.set_value("Company", company, "country", country)

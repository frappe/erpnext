# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	frappe.reload_doc("setup", "doctype", "company")
	if frappe.db.has_column('Company', 'default_terms'):
		rename_field('Company', "default_terms", "default_selling_terms")

		for company in frappe.get_all("Company", ["name", "default_selling_terms", "default_buying_terms"]):
			if company.default_selling_terms and not company.default_buying_terms:
				frappe.db.set_value("Company", company.name, "default_buying_terms", company.default_selling_terms)
	
	frappe.reload_doc("setup", "doctype", "terms_and_conditions")
	frappe.db.sql("update `tabTerms and Conditions` set selling=1, buying=1, hr=1")

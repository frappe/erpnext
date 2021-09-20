# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.regional.south_africa.setup import add_permissions, make_custom_fields


def condition():
	company = frappe.get_all("Company", filters={"country": "South Africa"})
	return bool(company)


# commented out to check patch tests
# documents_to_reload = [
# 	("regional", "doctype", "south_africa_vat_settings"),
# 	("regional", "report", "vat_audit_report"),
# 	("accounts", "doctype", "south_africa_vat_account"),
# ]


def execute():
	make_custom_fields()
	add_permissions()

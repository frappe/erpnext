"""Fix duplicate Customer first_name/last_name fields on Italian installations.

The Italy regional setup created Custom Fields with the same names as standard
fields, causing UniqueFieldnameError. This patch cleans up the duplicates and
uses Property Setters instead.
"""

import frappe


def execute():
	if not frappe.db.exists("Company", {"country": "Italy"}):
		return

	from erpnext.regional.italy.setup import setup_customer_name_fields

	setup_customer_name_fields()

import frappe

from ksa.install import make_custom_fields


def execute():
	company = frappe.get_all("Company", filters={"country": "Saudi Arabia"})
	if not company:
		return

	make_custom_fields()

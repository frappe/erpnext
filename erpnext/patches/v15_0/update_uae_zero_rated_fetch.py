import frappe

from erpnext.regional.united_arab_emirates.setup import make_custom_fields


def execute():
	if not frappe.db.get_value("Company", {"country": "United Arab Emirates"}):
		return

	make_custom_fields()

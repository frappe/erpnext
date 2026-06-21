import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	if not frappe.db.exists("Company", {"country": "United Arab Emirates"}):
		return

	create_custom_fields(
		{
			"Company": [
				{
					"fieldname": "company_name_in_arabic",
					"label": "Company Name in Arabic",
					"fieldtype": "Data",
					"insert_after": "company_name",
				}
			]
		},
		ignore_validate=True,
	)

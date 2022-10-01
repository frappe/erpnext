import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	company = frappe.get_all("Company", filters={"country": "India"})
	if not company:
		return

	custom_field = {
		"Finance Book": [
			{
				"fieldname": "for_income_tax",
				"label": "For Income Tax",
				"fieldtype": "Check",
				"insert_after": "finance_book_name",
				"description": "If the asset is put to use for less than 180 days, the first Depreciation Rate will be reduced by 50%.",
			}
		]
	}
	create_custom_fields(custom_field, update=1)

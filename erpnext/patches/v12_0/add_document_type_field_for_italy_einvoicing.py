import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	company = frappe.get_all("Company", filters={"country": "Italy"})
	if not company:
		return

	custom_fields = {
		"Sales Invoice": [
			dict(
				fieldname="type_of_document",
				label="Type of Document",
				fieldtype="Select",
				insert_after="customer_fiscal_code",
				options="\nTD01\nTD02\nTD03\nTD04\nTD05\nTD06\nTD16\nTD17\nTD18\nTD19\nTD20\nTD21\nTD22\nTD23\nTD24\nTD25\nTD26\nTD27",
			),
		]
	}

	create_custom_fields(custom_fields, update=True)

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	company = frappe.get_all("Company", filters={"country": "India"})
	if not company:
		return

	custom_fields = {
		"Sales Invoice": [
			dict(
				fieldname="eway_bill_validity",
				label="E-Way Bill Validity",
				fieldtype="Data",
				no_copy=1,
				print_hide=1,
				depends_on="ewaybill",
				read_only=1,
				allow_on_submit=1,
				insert_after="ewaybill",
			)
		]
	}
	create_custom_fields(custom_fields, update=True)

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	company = frappe.get_all("Company", filters={"country": "India"})
	if not company:
		return

	custom_fields = {
		"Delivery Note": [
			dict(
				fieldname="gst_category",
				label="GST Category",
				fieldtype="Select",
				insert_after="gst_vehicle_type",
				print_hide=1,
				options="\nRegistered Regular\nRegistered Composition\nUnregistered\nSEZ\nOverseas\nConsumer\nDeemed Export\nUIN Holders",
				fetch_from="customer.gst_category",
				fetch_if_empty=1,
			),
		]
	}

	create_custom_fields(custom_fields, update=True)
